"""CLI smoke tests (all against the seeded demo universe)."""

import json

import pytest

from trade_screener.cli import main


def test_scan_preset_table(capsys):
    assert main(["scan", "--demo", "--demo-n", "8", "--preset", "momentum"]) == 0
    out = capsys.readouterr().out
    assert "scanned: 8" in out
    assert "passed:" in out


def test_scan_criterion_json(capsys):
    assert main(["scan", "--demo", "--criterion", "rsi_14:between:20,80",
                 "--criterion", "vol_63:lte:0.5", "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["n_scanned"] == 12
    assert report["n_passed"] == len(report["passed_tickers"])


def test_scan_csv(capsys):
    assert main(["scan", "--demo", "--preset", "low-vol", "--format", "csv"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[0].startswith("ticker,passed")


def test_scan_no_criteria_errors():
    assert main(["scan", "--demo"]) == 2


def test_scan_bad_criterion_raises():
    with pytest.raises(ValueError):
        main(["scan", "--demo", "--criterion", "bogus"])


def test_score_preset_table(capsys):
    assert main(["score", "--demo", "--score-preset", "momentum-score", "--top", "5"]) == 0
    out = capsys.readouterr().out
    assert "rank" in out
    assert len([l for l in out.splitlines() if l.strip().startswith(tuple("12345"))]) == 5


def test_score_custom_weights(capsys):
    assert main(["score", "--demo", "--weight", "mom_126=1", "--weight", "vol_63=-0.5",
                 "--format", "json"]) == 0
    ranked = json.loads(capsys.readouterr().out)
    assert len(ranked) == 12
    assert ranked[0]["score"] >= ranked[-1]["score"]


def test_score_no_weights_errors():
    assert main(["score", "--demo"]) == 2


def test_metrics_command(capsys):
    assert main(["metrics", "--demo", "DEMO01"]) == 0
    out = capsys.readouterr().out
    assert "rsi_14" in out and "mom_126" in out


def test_metrics_unknown_ticker():
    assert main(["metrics", "--demo", "--demo-n", "4", "ZZZZ"]) == 2


def test_presets_command(capsys):
    assert main(["presets"]) == 0
    out = capsys.readouterr().out
    assert "momentum" in out and "value-score" in out


def test_license_command(capsys):
    assert main(["license"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True


def test_scan_with_fundamentals_csv(capsys, tmp_path):
    import csv
    path = tmp_path / "fund.csv"
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ticker", "pe"])
        for i in range(1, 13):
            w.writerow([f"DEMO{i:02d}", "12"])
    assert main(["scan", "--demo", "--fundamentals", str(path),
                 "--criterion", "pe:between:0,20", "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["n_passed"] == 12
