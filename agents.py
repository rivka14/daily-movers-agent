import json

from uipath_langchain.chat import UiPathChat

from state import AnalysisResult, Recommendation, ResearchResult, State, StockData
from tools import search

llm = UiPathChat(model="gpt-4o-mini-2024-07-18", temperature=0.7)


def _current_stock(state: State) -> StockData:
    return state.stocks[state.current_index]


def _parse_json(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        stripped = "\n".join(lines[1:-1]) if len(lines) > 2 else stripped

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return {}


async def research_node(state: State) -> State:
    stock = _current_stock(state)
    query = f"{stock.ticker} {stock.company_name} stock news today"
    raw_results = await search.arun(query)

    prompt = (
        f"You are a financial research assistant. Below are raw search results for "
        f"{stock.ticker} ({stock.company_name}).\n\n"
        f"{raw_results}\n\n"
        f"Produce a JSON object with exactly these keys:\n"
        f'  "ticker": "{stock.ticker}",\n'
        f'  "news_summary": "<2-3 sentence summary>",\n'
        f'  "key_events": ["<event1>", "<event2>", ...]\n\n'
        f"Return only the JSON object, no additional text."
    )
    response = await llm.ainvoke(prompt)
    assert isinstance(response.content, str)
    parsed = _parse_json(response.content)

    result = ResearchResult(
        ticker=parsed.get("ticker", stock.ticker),
        news_summary=parsed.get("news_summary", raw_results[:500]),
        key_events=parsed.get("key_events", []),
    )
    return state.model_copy(update={"research_results": state.research_results + [result]})


async def analyst_node(state: State) -> State:
    stock = _current_stock(state)
    research = state.research_results[-1]

    pe_str = f"{stock.pe_ratio:.2f}" if stock.pe_ratio is not None else "N/A"
    prompt = (
        f"You are a financial analyst. Analyse the following data for {stock.ticker} "
        f"({stock.company_name}).\n\n"
        f"Price: ${stock.price:.2f}  |  Change: ${stock.change:+.2f} ({stock.change_percent:+.2f}%)\n"
        f"Volume: {stock.volume:,}  |  Avg Vol (3M): {stock.avg_volume_3m:,}\n"
        f"Market Cap: {stock.market_cap}  |  P/E (TTM): {pe_str}\n"
        f"52-Week Range: ${stock.week_52_low:.2f} – ${stock.week_52_high:.2f}  |  52W Chg: {stock.week_52_change_pct:+.2f}%\n\n"
        f"News summary: {research.news_summary}\n"
        f"Key events: {research.key_events}\n\n"
        f"Produce a JSON object with exactly these keys:\n"
        f'  "ticker": "{stock.ticker}",\n'
        f'  "technical_analysis": "<2-3 sentences on price action, volume, momentum, and valuation>",\n'
        f'  "sentiment": "<one of: positive, negative, neutral>"\n\n'
        f"Return only the JSON object, no additional text."
    )
    response = await llm.ainvoke(prompt)
    assert isinstance(response.content, str)
    parsed = _parse_json(response.content)

    result = AnalysisResult(
        ticker=parsed.get("ticker", stock.ticker),
        technical_analysis=parsed.get("technical_analysis", "Analysis unavailable."),
        sentiment=parsed.get("sentiment", "neutral"),
    )
    return state.model_copy(update={"analysis_results": state.analysis_results + [result]})


async def strategist_node(state: State) -> State:
    stock = _current_stock(state)
    analysis = state.analysis_results[-1]

    pe_str = f"{stock.pe_ratio:.2f}" if stock.pe_ratio is not None else "N/A"
    prompt = (
        f"You are a senior investment strategist. Based on the following analysis for "
        f"{stock.ticker} ({stock.company_name}) make a recommendation.\n\n"
        f"Price: ${stock.price:.2f}  |  Change: ${stock.change:+.2f} ({stock.change_percent:+.2f}%)\n"
        f"Market Cap: {stock.market_cap}  |  P/E (TTM): {pe_str}\n"
        f"52-Week Range: ${stock.week_52_low:.2f} – ${stock.week_52_high:.2f}  |  52W Chg: {stock.week_52_change_pct:+.2f}%\n"
        f"Volume: {stock.volume:,}  |  Avg Vol (3M): {stock.avg_volume_3m:,}\n\n"
        f"Technical analysis: {analysis.technical_analysis}\n"
        f"Sentiment: {analysis.sentiment}\n\n"
        f"Produce a JSON object with exactly these keys:\n"
        f'  "ticker": "{stock.ticker}",\n'
        f'  "action": "<one of: Buy, Hold, Sell>",\n'
        f'  "reasoning": "<2-3 sentences justifying the recommendation, referencing valuation and momentum>",\n'
        f'  "confidence": <float between 0.0 and 1.0>\n\n'
        f"Return only the JSON object, no additional text."
    )
    response = await llm.ainvoke(prompt)
    assert isinstance(response.content, str)
    parsed = _parse_json(response.content)

    confidence = parsed.get("confidence", 0.5)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.5

    result = Recommendation(
        ticker=parsed.get("ticker", stock.ticker),
        action=parsed.get("action", "Hold"),
        reasoning=parsed.get("reasoning", "Insufficient data for a recommendation."),
        confidence=confidence,
    )
    return state.model_copy(update={"recommendations": state.recommendations + [result]})


async def supervisor_node(state: State) -> State:
    return state.model_copy(update={"current_index": state.current_index + 1})
