import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from output import _find_top_gainer, _find_top_loser, _find_top_recommended


def _stock(ticker: str, change_pct: float) -> dict:
    return {
        "ticker": ticker, "company_name": f"{ticker} Co", "price": 100.0,
        "change": change_pct, "change_percent": change_pct, "volume": 1_000_000,
        "avg_volume_3m": 800_000, "market_cap": "10B", "pe_ratio": 20.0,
        "week_52_change_pct": 10.0, "week_52_low": 80.0, "week_52_high": 120.0,
    }


STOCKS = [_stock("A", 5.0), _stock("B", -12.0), _stock("C", 18.0)]


def test_top_gainer():
    assert _find_top_gainer(STOCKS)["ticker"] == "C"


def test_top_loser():
    assert _find_top_loser(STOCKS)["ticker"] == "B"


def test_top_recommended_buys_first_then_holds():
    recs = [
        {"ticker": "A", "action": "Buy",  "reasoning": "ok", "confidence": 0.80},
        {"ticker": "B", "action": "Sell", "reasoning": "no", "confidence": 0.90},
        {"ticker": "C", "action": "Buy",  "reasoning": "yes","confidence": 0.95},
        {"ticker": "D", "action": "Hold", "reasoning": "meh","confidence": 0.60},
    ]
    top = _find_top_recommended(recs)
    # 2 Buys (C first by confidence, then A) + 1 Hold (D) to fill to 3
    assert [r["ticker"] for r in top] == ["C", "A", "D"]


def test_top_recommended_three_buys():
    recs = [
        {"ticker": "X", "action": "Buy", "reasoning": "a", "confidence": 0.70},
        {"ticker": "Y", "action": "Buy", "reasoning": "b", "confidence": 0.85},
        {"ticker": "Z", "action": "Buy", "reasoning": "c", "confidence": 0.92},
        {"ticker": "W", "action": "Buy", "reasoning": "d", "confidence": 0.60},
    ]
    top = _find_top_recommended(recs)
    assert len(top) == 3
    assert [r["ticker"] for r in top] == ["Z", "Y", "X"]
