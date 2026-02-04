import asyncio
import json
import re
from datetime import datetime, timezone

import httpx
import yfinance as yf
from bs4 import BeautifulSoup

from state import State, StockData

MOST_ACTIVE_URL = "https://finance.yahoo.com/markets/stocks/most-active/"
MAX_STOCKS = 20
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


def _float(val, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _int(val, default: int = 0) -> int:
    try:
        return int(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _fmt_mktcap(val) -> str:
    if val is None:
        return ""
    try:
        n = float(val)
        if n >= 1e12:
            return f"{n / 1e12:.3f}T"
        if n >= 1e9:
            return f"{n / 1e9:.3f}B"
        return f"{n / 1e6:.3f}M"
    except (TypeError, ValueError):
        return ""


def _find_quotes(blob: object) -> list[dict]:
    if isinstance(blob, list):
        if blob and isinstance(blob[0], dict) and "symbol" in blob[0]:
            return blob
        for item in blob:
            found = _find_quotes(item)
            if found:
                return found
    elif isinstance(blob, dict):
        if "quotes" in blob and isinstance(blob["quotes"], list):
            found = _find_quotes(blob["quotes"])
            if found:
                return found
        for val in blob.values():
            if isinstance(val, (dict, list)):
                found = _find_quotes(val)
                if found:
                    return found
    return []


def _try_parse_json(text: str) -> dict | list | None:
    stripped = text.strip()
    for candidate in (stripped, re.sub(r"^(?:var|let|const)\s+\S+\s*=\s*", "", stripped)):
        candidate = candidate.rstrip(";").strip()
        candidate = re.sub(r"^[\w.]+\s*=\s*", "", candidate)
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


async def _fetch_tickers(client: httpx.AsyncClient) -> list[str]:
    """Fetch ticker symbols from Yahoo Finance most active stocks page."""
    resp = await client.get(MOST_ACTIVE_URL, headers=HEADERS, timeout=30.0)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    for script in soup.find_all("script"):
        body = script.string or ""
        if "symbol" not in body:
            continue
        data = _try_parse_json(body)
        if data is None:
            continue
        quotes = _find_quotes(data)
        if not quotes:
            continue

        # Filter out cryptocurrencies and collect up to MAX_STOCKS
        tickers: list[str] = []
        for q in quotes:
            if q.get("quoteType") == "CRYPTOCURRENCY":
                continue
            symbol = q.get("symbol")
            if symbol:
                tickers.append(symbol)
            if len(tickers) >= MAX_STOCKS:
                break

        if tickers:
            return tickers

    return []


def _ticker_to_stock(ticker_obj) -> StockData | None:
    """Convert yfinance Ticker object to StockData."""
    try:
        info = ticker_obj.info
        ticker = info.get("symbol", "")
        if not ticker:
            return None

        # Extract earnings date
        earnings_date: str | None = None
        earnings_ts = info.get("earningsTimestamp")
        if earnings_ts:
            earnings_date = datetime.fromtimestamp(earnings_ts, tz=timezone.utc).strftime("%Y-%m-%d")

        # Calculate 52-week change percentage
        week_52_low = _float(info.get("fiftyTwoWeekLow"))
        week_52_high = _float(info.get("fiftyTwoWeekHigh"))
        current_price = _float(info.get("currentPrice") or info.get("regularMarketPrice"))

        week_52_change_pct = 0.0
        if week_52_low > 0:
            week_52_change_pct = ((current_price - week_52_low) / week_52_low) * 100

        return StockData(
            ticker=ticker,
            company_name=info.get("shortName", info.get("longName", ticker)),
            price=current_price,
            change=_float(info.get("regularMarketChange")),
            change_percent=_float(info.get("regularMarketChangePercent")),
            volume=_int(info.get("regularMarketVolume")),
            avg_volume_3m=_int(info.get("averageDailyVolume3Month")),
            market_cap=_fmt_mktcap(info.get("marketCap")),
            pe_ratio=_float(info.get("trailingPE")) if info.get("trailingPE") else None,
            week_52_change_pct=week_52_change_pct,
            week_52_low=week_52_low,
            week_52_high=week_52_high,
            earnings_date=earnings_date,
        )
    except Exception:
        return None


async def scrape_yahoo_finance() -> list[StockData]:
    """Scrape most active stocks from Yahoo Finance using yfinance library."""
    try:
        # Fetch tickers from Yahoo Finance page
        async with httpx.AsyncClient() as client:
            tickers = await _fetch_tickers(client)

        if not tickers:
            return []

        # Fetch detailed data using yfinance
        stocks: list[StockData] = []
        for ticker in tickers:
            try:
                ticker_obj = yf.Ticker(ticker)
                stock = _ticker_to_stock(ticker_obj)
                if stock:
                    stocks.append(stock)
            except Exception:
                # Skip tickers that fail to fetch
                pass

        return stocks

    except Exception:
        return []


async def scraper_node(state: State) -> State:
    if not state.stocks:
        stocks = await scrape_yahoo_finance()
        return state.model_copy(update={"stocks": stocks})
    return state


if __name__ == "__main__":
    stocks = asyncio.run(scrape_yahoo_finance())

    if not stocks:
        print("ERROR: scraper returned 0 stocks. Check network / Yahoo response.")
        raise SystemExit(1)

    payload = {"stocks": [s.model_dump() for s in stocks]}
    with open("input.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Scraped {len(stocks)} stocks → input.json")
    for s in stocks:
        print(f"  {s.ticker:6} {s.company_name:42} ${s.price:>10.2f}  {s.change_percent:+.2f}%  vol={s.volume:,}")
