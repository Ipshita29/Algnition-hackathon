"""Smoke test for backtest.py's CLI: runs end-to-end on tiny synthetic CSVs
and confirms it produces a well-formed results file without crashing. Not
exercising real accuracy (that needs the real dataset - see
docs/TECHNICAL_DOC.md for those numbers), just that the plumbing works.
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd


def _write_campaign_csv(path, campaign_name, campaign_type, n_days, daily_revenue, daily_spend):
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D")
    df = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "campaign_name": campaign_name,
        "campaign_type": campaign_type,
        "spend": daily_spend,
        "revenue": daily_revenue,
        "impressions": 1000,
        "clicks": 50,
        "conversions": 5,
    })
    df.to_csv(path, index=False)


def test_backtest_runs_end_to_end_on_tiny_synthetic_data(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # 100 days gives 30 held out, 70 for training - enough for XGB/Ridge,
    # short of Prophet's 60-row minimum so this stays fast.
    _write_campaign_csv(data_dir / "google_ads_test.csv", "Campaign_A", "shopping", 100, 500.0, 100.0)

    output_path = tmp_path / "backtest_results.csv"
    repo_root = Path(__file__).parent.parent

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "src" / "backtest.py"),
            "--data-dir", str(data_dir),
            "--holdout-days", "30",
            "--output", str(output_path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()

    results = pd.read_csv(output_path)
    assert len(results) == 1
    assert results.iloc[0]["campaign_name"] == "Campaign_A"
    assert "abs_error" in results.columns
