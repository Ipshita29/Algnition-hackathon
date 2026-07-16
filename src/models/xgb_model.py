"""XGBoost wrapper - the tribunal's feature learner.

Confidence intervals come from a 100-model bootstrap: each model is trained
on an 80% resample (with replacement, random_state 0-99) of the training
rows, then all 100 models predict a representative future daily revenue
rate. That rate is scaled by each requested period length (forecasts are
aggregate-period, not daily, per the challenge brief) and percentiles are
taken across the 100 scaled totals.
"""
import numpy as np
import xgboost as xgb

FEATURE_COLUMNS = [
    "spend",
    "lag_revenue_7d",
    "lag_revenue_28d",
    "rolling_mean_revenue_7d",
    "rolling_mean_roas_7d",
    "spend_growth_rate",
    "month",
    "week_of_year",
    "is_q4",
    "is_weekend",
]


class XGBModel:
    def __init__(self, n_bootstrap=100):
        self.models = []
        self.n_bootstrap = n_bootstrap

    def fit(self, X, y):
        X = X[FEATURE_COLUMNS].reset_index(drop=True)
        y = np.asarray(y)
        n = len(X)

        self.models = []
        for seed in range(self.n_bootstrap):
            rng = np.random.RandomState(seed)
            idx = rng.choice(n, size=max(1, int(n * 0.8)), replace=True)

            model = xgb.XGBRegressor(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=seed,
                n_jobs=-1,
            )
            model.fit(X.iloc[idx], y[idx])
            self.models.append(model)
        return self

    def predict(self, future_row, periods=(30, 60, 90)):
        """future_row: single-row DataFrame with FEATURE_COLUMNS."""
        daily_preds = np.array([m.predict(future_row[FEATURE_COLUMNS])[0] for m in self.models])
        daily_preds = np.clip(daily_preds, a_min=0, a_max=None)

        results = {}
        for period_days in periods:
            totals = daily_preds * period_days
            p10, p50, p90 = np.percentile(totals, [10, 50, 90])
            results[period_days] = {"p10": float(p10), "p50": float(p50), "p90": float(p90)}
        return results
