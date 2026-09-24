"""Tests for demo data, fundamentals loading, and adapters."""

import csv

import pytest

from trade_screener import demo_fundamentals, demo_universe
from trade_screener.adapters import (
    metrics_for_optimize,
    tickers_from_universe,
    to_agent_ideas,
    to_backtest_universe,
)
from trade_screener.demo import ARCHETYPES
from trade_screener.fundamentals import fundamentals_from_rows, load_fundamentals_csv
from trade_screener.screen import preset_criteria, screen


def test_demo_deterministic():
    a = demo_universe(n=8, days=100, seed=3)
    b = demo_universe(n=8, days=100, seed=3)
    assert a == b
    c = demo_universe(n=8, days=100, seed=4)
    assert a != c


def test_demo_bar_contract():
    data = demo_universe(n=3, days=50, seed=3)
    for ticker, bars in data.items():
        assert ticker.startswith("DEMO")
        assert len(bars) == 50
        for bar in bars:
            assert set(bar) == {"date", "open", "high", "low", "close", "volume"}
            assert bar["low"] <= bar["close"] <= bar["high"]
            assert bar["low"] <= bar["open"] <= bar["high"]
            assert bar["volume"] > 0


def test_demo_archetypes_differ():
    data = demo_universe(n=5, days=300, seed=9)
    vols = {}
    for i, ticker in enumerate(sorted(data)):
        from trade_screener.indicators import realized_vol, closes
        vols[ARCHETYPES[i]] = realized_vol(closes(data[ticker]), 63)
    assert vols["high-vol"] > vols["flat"]
    assert vols["high-vol"] > vols["uptrend"]


def test_demo_fundamentals_shape():
    tickers = ["AAA", "BBB"]
    fund = demo_fundamentals(tickers, seed=5)
    assert set(fund) == {"AAA", "BBB"}
    for entry in fund.values():
        assert entry["pe"] > 0
        assert entry["market_cap"] > 0


def test_fundamentals_from_rows_normalizes():
    rows = [
        {"ticker": " aapl ", "pe": "25.5", "pb": "", "dividend_yield": "0.005", "beta": "bad"},
        {"ticker": "", "pe": "10"},
        {"ticker": "MSFT", "pe": 30},
    ]
    out = fundamentals_from_rows(rows)
    assert set(out) == {"AAPL", "MSFT"}
    assert out["AAPL"]["pe"] == 25.5
    assert "pb" not in out["AAPL"]  # empty string skipped
    assert "beta" not in out["AAPL"]  # unparseable skipped
    assert out["MSFT"]["pe"] == 30.0  # numeric input accepted


def test_load_fundamentals_csv(tmp_path):
    path = tmp_path / "fund.csv"
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ticker", "pe", "market_cap", "name"])
        w.writerow(["AAPL", "25", "3000000000000", "Apple"])
    out = load_fundamentals_csv(path)
    assert out["AAPL"]["pe"] == 25.0
    assert out["AAPL"]["name"] == "Apple"


def test_tickers_from_plain_text_fallback(tmp_path):
    path = tmp_path / "watch.txt"
    path.write_text("aapl\n\nMSFT\n")
    name, tickers = tickers_from_universe(str(path))
    assert tickers == ["AAPL", "MSFT"]
    assert name == "watch"


def test_tickers_from_csv_fallback(tmp_path):
    path = tmp_path / "uni.csv"
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ticker", "kind"])
        w.writerow(["AAPL", "stock"])
    name, tickers = tickers_from_universe(str(path))
    assert tickers == ["AAPL"]


def test_tickers_missing_file():
    with pytest.raises(FileNotFoundError):
        tickers_from_universe("/nope/missing.csv")


def test_to_backtest_universe():
    data = demo_universe(n=6, days=300, seed=2)
    report = screen(data, preset_criteria("momentum"), universe="demo")
    payload = to_backtest_universe(report)
    assert payload["universe"] == "demo"
    assert payload["tickers"] == list(report.passed_tickers)
    assert payload["n_scanned"] == 6


def test_to_agent_ideas():
    from trade_screener import preset_score_spec, score
    data = demo_universe(n=6, days=300, seed=2)
    fund = demo_fundamentals(list(data), seed=2)
    report = screen(data, preset_criteria("momentum"), fund)
    ranked = score(data, preset_score_spec("momentum-score"), fund)
    ideas = to_agent_ideas(report, ranked)
    assert len(ideas) == len(report.passed_tickers)
    for idea in ideas:
        assert idea["kind"] == "screen_pass"
        assert "thesis" in idea and idea["thesis"]
    # rank-1 idea first when scoring supplied
    if ideas:
        assert ideas[0]["rank"] == 1


def test_metrics_for_optimize():
    data = demo_universe(n=4, days=300, seed=2)
    report = screen(data, preset_criteria("momentum"))
    out = metrics_for_optimize(list(report.rows))
    assert set(out) == {r.ticker for r in report.rows}
    assert set(out["DEMO01"]) == {"vol_63", "mom_126"}
