"""Held-out backtest: how accurate are the tribunal's forecasts, really?

Everything verified elsewhere in this pipeline (no NaNs, P10<=P50<=P90,
right shape) is internal consistency, not accuracy. This holds out the
last --holdout-days of the real dataset, trains a fresh tribunal on
everything before that cutoff, forecasts holdout-days ahead, and compares
against what actually happened in the held-out window - real MAE/RMSE,
P10-P90 empirical coverage, and a comparison against a naive "revenue
stays at its trailing rate" baseline.

Not called from run.sh - a one-time (or occasional) evaluation tool, not
part of the scored pipeline.

CLI: python src/backtest.py --data-dir ./data --holdout-days 30 --output backtest_results.csv
"""
import argparse

import numpy as np
import pandas as pd

from generate_features import build_features
from models.tribunal import ForecastingTribunal


def main():
    parser = argparse.ArgumentParser(description="Backtest the tribunal against real held-out data")
    parser.add_argument("--data-dir", default="./data")
    parser.add_argument("--holdout-days", type=int, default=30)
    parser.add_argument("--output", default=None, help="Optional CSV path for per-campaign backtest results")
    args = parser.parse_args()

    df = build_features(args.data_dir)
    cutoff = df["date"].max() - pd.Timedelta(days=args.holdout_days)
    train_df = df[df["date"] <= cutoff].copy()
    test_df = df[df["date"] > cutoff].copy()

    print(f"Full data: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"Training on data through {cutoff.date()}, evaluating against the {args.holdout_days} days after\n")

    tribunal = ForecastingTribunal().fit(train_df)
    predictions = tribunal.predict(train_df, periods=(args.holdout_days,))

    actual_revenue = test_df.groupby(["channel", "campaign_name"])["revenue"].sum()

    # Naive baseline: "revenue stays at its trailing 28-day rate" - what the
    # tribunal should be beating, not just a well-formed number.
    def _trailing_daily_rate(group):
        return group.sort_values("date")["revenue"].tail(28).mean()

    baseline_daily = train_df.groupby(["channel", "campaign_name"]).apply(_trailing_daily_rate, include_groups=False)

    rows = []
    for key, campaign_periods in predictions.items():
        if key not in actual_revenue.index:
            continue  # campaign has no data in the held-out window - can't evaluate it
        channel, campaign_name = key
        actual = actual_revenue.loc[key]
        pred = campaign_periods[args.holdout_days]
        baseline_pred = (
            baseline_daily.loc[key] * args.holdout_days if key in baseline_daily.index else np.nan
        )

        rows.append({
            "channel": channel,
            "campaign_name": campaign_name,
            "actual_revenue": actual,
            "predicted_p10": pred["revenue_p10"],
            "predicted_p50": pred["revenue_p50"],
            "predicted_p90": pred["revenue_p90"],
            "naive_baseline": baseline_pred,
            "abs_error": abs(actual - pred["revenue_p50"]),
            "baseline_abs_error": abs(actual - baseline_pred) if pd.notna(baseline_pred) else np.nan,
            "within_p10_p90": pred["revenue_p10"] <= actual <= pred["revenue_p90"],
            "uncertainty_level": pred["uncertainty_level"],
        })

    result_df = pd.DataFrame(rows)
    if result_df.empty:
        print("No campaigns had data in both the training window and the held-out window - nothing to evaluate.")
        return

    mae = result_df["abs_error"].mean()
    rmse = np.sqrt((result_df["abs_error"] ** 2).mean())
    coverage = result_df["within_p10_p90"].mean() * 100
    baseline_mae = result_df["baseline_abs_error"].mean()
    improvement = (1 - mae / baseline_mae) * 100 if baseline_mae > 0 else float("nan")

    print(f"Evaluated {len(result_df)} campaigns with data in both windows\n")
    print(f"Tribunal MAE:  ${mae:,.2f}")
    print(f"Tribunal RMSE: ${rmse:,.2f}")
    print(f"Naive baseline (trailing 28-day rate) MAE: ${baseline_mae:,.2f}")
    print(f"Tribunal improvement over naive baseline: {improvement:.1f}%")
    print(
        f"P10-P90 empirical coverage: {coverage:.1f}% "
        "(how often the actual fell inside the forecast range)"
    )

    by_uncertainty = result_df.groupby("uncertainty_level")["abs_error"].mean().sort_values()
    print("\nMean absolute error by uncertainty_level (should increase LOW -> MODERATE -> HIGH " "if the disagreement score is well-calibrated):")
    print(by_uncertainty.to_string())

    if args.output:
        result_df.to_csv(args.output, index=False)
        print(f"\nPer-campaign results written to {args.output}")


if __name__ == "__main__":
    main()
