from state import StockData


def _make_stock(**overrides) -> StockData:
    defaults = dict(
        ticker="TEST",
        company_name="Test Corp",
        price=100.0,
        change=5.0,
        change_percent=5.26,
        volume=10_000_000,
        avg_volume_3m=8_000_000,
        market_cap="10B",
        pe_ratio=25.0,
        week_52_change_pct=30.0,
        week_52_low=75.0,
        week_52_high=110.0,
    )
    defaults.update(overrides)
    return StockData(**defaults)


def test_all_fields_present():
    stock = _make_stock()
    assert stock.ticker == "TEST"
    assert stock.change == 5.0
    assert stock.avg_volume_3m == 8_000_000
    assert stock.market_cap == "10B"
    assert stock.pe_ratio == 25.0
    assert stock.week_52_change_pct == 30.0
    assert stock.week_52_low == 75.0
    assert stock.week_52_high == 110.0


def test_pe_ratio_nullable():
    stock = _make_stock(pe_ratio=None)
    assert stock.pe_ratio is None


def test_earnings_date_defaults_none():
    stock = _make_stock()
    assert stock.earnings_date is None


def test_earnings_date_set():
    stock = _make_stock(earnings_date="2026-03-15")
    assert stock.earnings_date == "2026-03-15"
