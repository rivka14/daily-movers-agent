from typing import Annotated, TypedDict
import operator


class StockData(TypedDict):
    ticker: str
    company_name: str
    price: float
    change_percent: float
    volume: int


class ResearchResult(TypedDict):
    ticker: str
    news_summary: str
    key_events: list[str]


class AnalysisResult(TypedDict):
    ticker: str
    technical_analysis: str
    sentiment: str


class Recommendation(TypedDict):
    ticker: str
    action: str
    reasoning: str
    confidence: float


class AgentState(TypedDict):
    stocks: list[StockData]
    current_index: int
    research_results: Annotated[list[ResearchResult], operator.add]
    analysis_results: Annotated[list[AnalysisResult], operator.add]
    recommendations: Annotated[list[Recommendation], operator.add]
    excel_path: str | None
    email_summary: str | None
