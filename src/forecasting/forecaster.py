"""
Forecasting module — time-series forecasting of monthly order volume.
Tests multiple models, selects best by out-of-sample performance.
Uses expanding-window cross-validation (no random split for time series).
"""
import pandas as pd
import numpy as np
import os
import json
import warnings
import logging
from datetime import datetime

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MARTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "marts")
)
FORECASTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "forecasts")
)


# ── Metrics ────────────────────────────────────────────────────────────────────
def mae(actual, predicted):
    return float(np.mean(np.abs(np.array(actual) - np.array(predicted))))

def rmse(actual, predicted):
    return float(np.sqrt(np.mean((np.array(actual) - np.array(predicted)) ** 2)))

def smape(actual, predicted):
    a = np.array(actual)
    p = np.array(predicted)
    denom = (np.abs(a) + np.abs(p)) / 2
    denom = np.where(denom == 0, 1e-10, denom)
    return float(np.mean(np.abs(a - p) / denom) * 100)


# ── Model implementations ──────────────────────────────────────────────────────
def naive_forecast(series: np.ndarray, h: int) -> np.ndarray:
    """Naive: last observed value repeated."""
    return np.full(h, series[-1])


def moving_average_forecast(series: np.ndarray, h: int, window: int = 3) -> np.ndarray:
    """Moving average of last `window` observations."""
    avg = np.mean(series[-window:])
    return np.full(h, avg)


def exponential_smoothing_forecast(series: np.ndarray, h: int, alpha: float = 0.3) -> np.ndarray:
    """Simple exponential smoothing with fixed alpha."""
    smoothed = series[0]
    for val in series[1:]:
        smoothed = alpha * val + (1 - alpha) * smoothed
    return np.full(h, smoothed)


def holt_winters_forecast(series: pd.Series, h: int):
    """Holt-Winters additive model via statsmodels."""
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        if len(series) < 6:
            return None, None
        # Try seasonal model if enough data
        seasonal_periods = 12
        if len(series) >= 2 * seasonal_periods:
            model = ExponentialSmoothing(
                series, trend="add", seasonal="add",
                seasonal_periods=seasonal_periods, initialization_method="estimated"
            )
        else:
            model = ExponentialSmoothing(
                series, trend="add", seasonal=None,
                initialization_method="estimated"
            )
        fit = model.fit(optimized=True, use_brute=True)
        forecast = fit.forecast(h)
        # Simple CI: ±1.96 * residual std
        resid_std = float(np.std(fit.resid))
        ci_lower = forecast - 1.96 * resid_std
        ci_upper = forecast + 1.96 * resid_std
        return forecast.values, (ci_lower.values, ci_upper.values)
    except Exception as e:
        logger.warning(f"Holt-Winters failed: {e}")
        return None, None


def arima_forecast(series: pd.Series, h: int):
    """ARIMA/SARIMA via statsmodels auto-selection."""
    try:
        from statsmodels.tsa.arima.model import ARIMA
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        best_aic = np.inf
        best_fit = None
        best_order = None

        # Grid search over small ARIMA parameter space
        for p in range(0, 3):
            for d in range(0, 2):
                for q in range(0, 3):
                    try:
                        model = ARIMA(series, order=(p, d, q))
                        fit = model.fit()
                        if fit.aic < best_aic:
                            best_aic = fit.aic
                            best_fit = fit
                            best_order = (p, d, q)
                    except Exception:
                        continue

        if best_fit is None:
            return None, None, None

        forecast_obj = best_fit.get_forecast(h)
        forecast_vals = forecast_obj.predicted_mean.values
        ci = forecast_obj.conf_int(alpha=0.05)
        ci_lower = ci.iloc[:, 0].values
        ci_upper = ci.iloc[:, 1].values

        return forecast_vals, (ci_lower, ci_upper), best_order

    except Exception as e:
        logger.warning(f"ARIMA failed: {e}")
        return None, None, None


# ── Cross-validation ───────────────────────────────────────────────────────────
def expanding_window_cv(series: np.ndarray, min_train: int = 12, h: int = 1) -> dict:
    """
    Expanding window time-series cross-validation.
    Trains on [0:t], forecasts [t:t+h], steps through all valid windows.
    Returns dict of {model_name: [MAE, RMSE, sMAPE]}.
    """
    n = len(series)
    results = {
        "naive": [], "moving_avg_3": [], "exp_smoothing": []
    }
    actuals_all = {"naive": [], "moving_avg_3": [], "exp_smoothing": []}
    preds_all = {k: [] for k in results}

    for t in range(min_train, n - h + 1):
        train = series[:t]
        actual = series[t:t+h]

        preds = {
            "naive": naive_forecast(train, h),
            "moving_avg_3": moving_average_forecast(train, h, window=3),
            "exp_smoothing": exponential_smoothing_forecast(train, h, alpha=0.3),
        }
        for name, pred in preds.items():
            actuals_all[name].extend(actual.tolist())
            preds_all[name].extend(pred.tolist())

    cv_metrics = {}
    for name in results:
        if actuals_all[name]:
            cv_metrics[name] = {
                "MAE": round(mae(actuals_all[name], preds_all[name]), 2),
                "RMSE": round(rmse(actuals_all[name], preds_all[name]), 2),
                "sMAPE": round(smape(actuals_all[name], preds_all[name]), 2),
            }

    return cv_metrics


# ── Main forecasting pipeline ──────────────────────────────────────────────────
def build_monthly_series(fact: pd.DataFrame) -> pd.Series:
    """Build clean monthly order count series sorted by year_month_str."""
    monthly = (
        fact.groupby("year_month_str")["order_id"]
        .count()
        .reset_index()
        .rename(columns={"order_id": "orders"})
        .sort_values("year_month_str")
    )
    monthly.index = pd.PeriodIndex(monthly["year_month_str"], freq="M")
    return monthly["orders"]


def run_forecasting(fact: pd.DataFrame, horizon: int = 3) -> dict:
    """
    Full forecasting pipeline:
    1. Build monthly series
    2. Cross-validate simple models
    3. Fit Holt-Winters and ARIMA
    4. Compare all models
    5. Select best by sMAPE
    6. Return forecast + intervals + model comparison
    """
    logger.info("Starting forecasting pipeline...")
    series = build_monthly_series(fact)
    series_values = series.values.astype(float)
    n = len(series)
    logger.info(f"  Series length: {n} months ({series.index[0]} → {series.index[-1]})")

    if n < 12:
        logger.warning("Insufficient data for reliable forecasting (need >= 12 months).")
        return {"error": "Insufficient data", "n_months": n}

    # ── Cross-validate simple models ──────────────────────────────────────────
    logger.info("  Running expanding-window cross-validation...")
    cv_results = expanding_window_cv(series_values, min_train=12, h=1)
    logger.info(f"  CV results: {cv_results}")

    # ── Fit Holt-Winters ──────────────────────────────────────────────────────
    logger.info("  Fitting Holt-Winters...")
    hw_forecast, hw_ci = holt_winters_forecast(series, horizon)

    # ── Fit ARIMA ────────────────────────────────────────────────────────────
    logger.info("  Fitting ARIMA (grid search)...")
    arima_fc, arima_ci, arima_order = arima_forecast(series, horizon)

    # ── Compute in-sample metrics for HW and ARIMA ────────────────────────────
    # Use last 6 months as pseudo-test set for comparison
    test_size = min(6, n // 3)
    train_s = series.iloc[:-test_size]
    test_s = series.iloc[-test_size:]

    hw_test, _ = holt_winters_forecast(train_s, test_size)
    arima_test, _, _ = arima_forecast(train_s, test_size)

    if hw_test is not None:
        cv_results["holt_winters"] = {
            "MAE": round(mae(test_s.values, hw_test), 2),
            "RMSE": round(rmse(test_s.values, hw_test), 2),
            "sMAPE": round(smape(test_s.values, hw_test), 2),
        }
    if arima_test is not None:
        cv_results["arima"] = {
            "MAE": round(mae(test_s.values, arima_test), 2),
            "RMSE": round(rmse(test_s.values, arima_test), 2),
            "sMAPE": round(smape(test_s.values, arima_test), 2),
        }

    # ── Select best model by sMAPE ────────────────────────────────────────────
    best_model = min(cv_results, key=lambda m: cv_results[m].get("sMAPE", 999))
    logger.info(f"  Best model: {best_model} (sMAPE={cv_results[best_model]['sMAPE']:.1f}%)")

    # ── Generate final forecast using best model ──────────────────────────────
    if best_model == "holt_winters" and hw_forecast is not None:
        final_fc = hw_forecast
        final_ci = hw_ci
    elif best_model == "arima" and arima_fc is not None:
        final_fc = arima_fc
        final_ci = arima_ci
    elif best_model == "moving_avg_3":
        final_fc = moving_average_forecast(series_values, horizon, window=3)
        std_resid = np.std(np.diff(series_values[-6:]))
        final_ci = (final_fc - 1.96 * std_resid, final_fc + 1.96 * std_resid)
    elif best_model == "exp_smoothing":
        final_fc = exponential_smoothing_forecast(series_values, horizon, alpha=0.3)
        std_resid = np.std(np.diff(series_values[-6:]))
        final_ci = (final_fc - 1.96 * std_resid, final_fc + 1.96 * std_resid)
    else:
        final_fc = naive_forecast(series_values, horizon)
        std_resid = np.std(series_values[-6:])
        final_ci = (final_fc - 1.96 * std_resid, final_fc + 1.96 * std_resid)

    # ── Build forecast periods ────────────────────────────────────────────────
    last_period = series.index[-1]
    forecast_periods = [str(last_period + i) for i in range(1, horizon + 1)]

    forecast_df = pd.DataFrame({
        "year_month_str": forecast_periods,
        "forecast_orders": np.maximum(0, np.round(final_fc)).astype(int),
        "ci_lower": np.maximum(0, np.round(final_ci[0])).astype(int),
        "ci_upper": np.maximum(0, np.round(final_ci[1])).astype(int),
        "model": best_model,
    })

    # ── Historical series DataFrame ───────────────────────────────────────────
    historical_df = pd.DataFrame({
        "year_month_str": series.index.astype(str).tolist(),
        "actual_orders": series.values.tolist(),
    })

    result = {
        "generated_at": datetime.now().isoformat(),
        "series_length": n,
        "horizon": horizon,
        "best_model": best_model,
        "best_model_metrics": cv_results[best_model],
        "all_model_metrics": cv_results,
        "arima_order": str(arima_order) if arima_order else None,
        "forecast": forecast_df,
        "historical": historical_df,
        "disclaimer": (
            "This is a statistical forecast based on historical patterns. "
            "It is not a guaranteed prediction of future outcomes. "
            "External factors (seasonality, market events, platform changes) "
            "are not captured in this model."
        ),
    }

    logger.info("Forecasting complete.")
    logger.info(f"  Forecast for next {horizon} months:\n{forecast_df.to_string(index=False)}")
    return result


def save_forecast(result: dict, output_dir: str = FORECASTS_PATH) -> str:
    """Save forecast results."""
    os.makedirs(output_dir, exist_ok=True)

    # Save DataFrames as parquet
    if "forecast" in result and isinstance(result["forecast"], pd.DataFrame):
        result["forecast"].to_parquet(
            os.path.join(output_dir, "forecast_future.parquet"), index=False
        )
    if "historical" in result and isinstance(result["historical"], pd.DataFrame):
        result["historical"].to_parquet(
            os.path.join(output_dir, "forecast_historical.parquet"), index=False
        )

    # Save summary JSON (excluding DataFrames)
    summary = {k: v for k, v in result.items()
                if not isinstance(v, pd.DataFrame)}
    path = os.path.join(output_dir, "forecast_results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Forecast saved: {path}")
    return path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
    fact = pd.read_parquet(os.path.join(MARTS_PATH, "fact_orders.parquet"))
    result = run_forecasting(fact, horizon=3)
    save_forecast(result)

    print("\nModel Comparison:")
    for model, metrics in result["all_model_metrics"].items():
        flag = " ← BEST" if model == result["best_model"] else ""
        print(f"  {model:<20} MAE={metrics['MAE']:>7.1f}  RMSE={metrics['RMSE']:>7.1f}  "
              f"sMAPE={metrics['sMAPE']:>5.1f}%{flag}")

    print(f"\nForecast ({result['horizon']}-month horizon):")
    print(result["forecast"].to_string(index=False))
    print(f"\nNote: {result['disclaimer']}")
