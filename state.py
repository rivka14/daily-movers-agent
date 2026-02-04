from pydantic import BaseModel, Field


class StockData(BaseModel):
    ticker: str
    company_name: str
    price: float
    change: float
    change_percent: float
    volume: int
    avg_volume_3m: int
    market_cap: str
    pe_ratio: float | None = None
    week_52_change_pct: float
    week_52_low: float
    week_52_high: float
    earnings_date: str | None = None


class ResearchResult(BaseModel):
    ticker: str
    news_summary: str
    key_events: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    ticker: str
    technical_analysis: str
    sentiment: str


class Recommendation(BaseModel):
    ticker: str
    action: str
    reasoning: str
    confidence: float


class Input(BaseModel):
    stocks: list[StockData] = Field(default_factory=list)


class State(BaseModel):
    stocks: list[StockData] = Field(default_factory=list)
    current_index: int = 0
    research_results: list[ResearchResult] = Field(default_factory=list)
    analysis_results: list[AnalysisResult] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    excel_path: str | None = None
    email_summary: str | None = None


class Output(BaseModel):
    excel_path: str | None = None
    email_summary: str | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)
