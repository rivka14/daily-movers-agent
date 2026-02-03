import json
import warnings

from langchain_google_vertexai import ChatVertexAI

warnings.filterwarnings("ignore", message=".*ChatVertexAI.*deprecated.*")

from state import AgentState, StockData
from tools import search

llm = ChatVertexAI(
    model="gemini-2.0-flash",
)


def _current_stock(state: AgentState) -> StockData:
    """Return the stock dict at the current loop index."""
    return state["stocks"][state["current_index"]]


def _parse_json(text: str) -> dict:
    """Extract the first JSON object from an LLM response.

    Handles the common case where the model wraps output in ```json … ``` fences.
    Falls back to an empty dict on failure so the graph keeps running.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        stripped = "\n".join(lines[1:-1]) if len(lines) > 2 else stripped

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return {}


def research_node(state: AgentState) -> dict:
    """Search for news about the current stock and return a ResearchResult."""
    stock = _current_stock(state)
    query = f"{stock['ticker']} {stock['company_name']} stock news today"
    raw_results = search.run(query)

    prompt = (
        f"You are a financial research assistant. Below are raw search results for "
        f"{stock['ticker']} ({stock['company_name']}).\n\n"
        f"{raw_results}\n\n"
        f"Produce a JSON object with exactly these keys:\n"
        f'  "ticker": "{stock["ticker"]}",\n'
        f'  "news_summary": "<2-3 sentence summary>",\n'
        f'  "key_events": ["<event1>", "<event2>", ...]\n\n'
        f"Return only the JSON object, no additional text."
    )
    response = llm.invoke(prompt)
    assert isinstance(response.content, str)
    parsed = _parse_json(response.content)

    result = {
        "ticker": parsed.get("ticker", stock["ticker"]),
        "news_summary": parsed.get("news_summary", raw_results[:500]),
        "key_events": parsed.get("key_events", []),
    }
    return {"research_results": [result]}


def analyst_node(state: AgentState) -> dict:
    """Analyse sentiment and technical factors for the current stock."""
    stock = _current_stock(state)
    research = state["research_results"][-1]

    prompt = (
        f"You are a financial analyst. Analyse the following data for {stock['ticker']} "
        f"({stock['company_name']}).\n\n"
        f"Stock price: ${stock['price']}, Change: {stock['change_percent']}%, "
        f"Volume: {stock['volume']:,}\n\n"
        f"News summary: {research['news_summary']}\n"
        f"Key events: {research['key_events']}\n\n"
        f"Produce a JSON object with exactly these keys:\n"
        f'  "ticker": "{stock["ticker"]}",\n'
        f'  "technical_analysis": "<2-3 sentences on price action, volume, momentum>",\n'
        f'  "sentiment": "<one of: positive, negative, neutral>"\n\n'
        f"Return only the JSON object, no additional text."
    )
    response = llm.invoke(prompt)
    assert isinstance(response.content, str)
    parsed = _parse_json(response.content)

    result = {
        "ticker": parsed.get("ticker", stock["ticker"]),
        "technical_analysis": parsed.get("technical_analysis", "Analysis unavailable."),
        "sentiment": parsed.get("sentiment", "neutral"),
    }
    return {"analysis_results": [result]}


def strategist_node(state: AgentState) -> dict:
    """Generate a Buy/Hold/Sell recommendation for the current stock."""
    stock = _current_stock(state)
    analysis = state["analysis_results"][-1]

    prompt = (
        f"You are a senior investment strategist. Based on the following analysis for "
        f"{stock['ticker']} ({stock['company_name']}) make a recommendation.\n\n"
        f"Price: ${stock['price']}, Change: {stock['change_percent']}%, "
        f"Volume: {stock['volume']:,}\n"
        f"Technical analysis: {analysis['technical_analysis']}\n"
        f"Sentiment: {analysis['sentiment']}\n\n"
        f"Produce a JSON object with exactly these keys:\n"
        f'  "ticker": "{stock["ticker"]}",\n'
        f'  "action": "<one of: Buy, Hold, Sell>",\n'
        f'  "reasoning": "<2-3 sentences justifying the recommendation>",\n'
        f'  "confidence": <float between 0.0 and 1.0>\n\n'
        f"Return only the JSON object, no additional text."
    )
    response = llm.invoke(prompt)
    assert isinstance(response.content, str)
    parsed = _parse_json(response.content)

    confidence = parsed.get("confidence", 0.5)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.5

    result = {
        "ticker": parsed.get("ticker", stock["ticker"]),
        "action": parsed.get("action", "Hold"),
        "reasoning": parsed.get("reasoning", "Insufficient data for a recommendation."),
        "confidence": confidence,
    }
    return {"recommendations": [result]}


def supervisor_node(state: AgentState) -> dict:
    """Increment current_index to advance to the next stock."""
    return {"current_index": state["current_index"] + 1}
