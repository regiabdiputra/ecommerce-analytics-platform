"""
Anomaly Detection module — detects unusual patterns in business metrics.
Methods: rolling z-score, IQR, STL decomposition residuals.
Severity levels: Normal / Watch / Warning / Critical
"""
import pandas as pd
import numpy as np
import os
import json
import logging
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MARTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "marts")
)
REPORTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports")
)


def _severity(z_score: float) -> str:
    """Map z-score magnitude to severity level."""
    az = abs(z_score)
    if az < 1.5:
        return "Normal"
    if az < 2.0:
        return "Watch"
    if az < 3.0:
        return "Warning"
    return "Critical"


def rolling_zscore_anomalies(series: pd.Series, window: int = 6,
                              label: str = "metric") -> pd.DataFrame:
    """
    Detect anomalies using rolling z-score.
    z = (x - rolling_mean) / rolling_std
    Threshold methodology: industry standard z-score bands.
    |z| < 1.5 → Normal, 1.5–2.0 → Watch, 2.0–3.0 → Warning, >3.0 → Critical
    """
    df = pd.DataFrame({"period": series.index, "value": series.values})
    df["rolling_mean"] = df["value"].rolling(window, min_periods=3).mean()
    df["rolling_std"] = df["value"].rolling(window, min_periods=3).std()
    df["z_score"] = (df["value"] - df["rolling_mean"]) / df["rolling_std"].replace(0, np.nan)
    df["z_score"] = df["z_score"].fillna(0)
    df["severity"] = df["z_score"].apply(_severity)
    df["metric"] = label
    df["anomaly_flag"] = (df["severity"] != "Normal").astype(int)
    return df


def iqr_anomalies(series: pd.Series, label: str = "metric") -> pd.DataFrame:
    """
    Detect anomalies using IQR method.
    Outlier if value < Q1 - 1.5*IQR or value > Q3 + 1.5*IQR.
    Severe if beyond Q1 - 3*IQR or Q3 + 3*IQR.
    """
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower_warn = q1 - 1.5 * iqr
    upper_warn = q3 + 1.5 * iqr
    lower_crit = q1 - 3.0 * iqr
    upper_crit = q3 + 3.0 * iqr

    def _iqr_severity(v):
        if v < lower_crit or v > upper_crit:
            return "Critical"
        if v < lower_warn or v > upper_warn:
            return "Warning"
        return "Normal"

    df = pd.DataFrame({"period": series.index, "value": series.values})
    df["q1"] = q1
    df["q3"] = q3
    df["iqr"] = iqr
    df["lower_bound"] = lower_warn
    df["upper_bound"] = upper_warn
    df["severity"] = df["value"].apply(_iqr_severity)
    df["metric"] = label
    df["anomaly_flag"] = (df["severity"] != "Normal").astype(int)
    return df


def stl_residual_anomalies(series: pd.Series, label: str = "metric") -> pd.DataFrame:
    """
    STL decomposition — detect anomalies in residuals.
    Requires >= 2 full seasonal cycles (24+ months for yearly seasonality).
    Falls back to rolling z-score if insufficient data.
    """
    if len(series) < 24:
        logger.info(f"  STL: insufficient data ({len(series)} pts), falling back to rolling z-score")
        return rolling_zscore_anomalies(series, window=6, label=label)

    try:
        from statsmodels.tsa.seasonal import STL
        stl = STL(series, seasonal=13, period=12, robust=True)
        result = stl.fit()
        residuals = pd.Series(result.resid, index=series.index)
        resid_mean = residuals.mean()
        resid_std = residuals.std()
        z_scores = (residuals - resid_mean) / resid_std if resid_std > 0 else residuals * 0

        df = pd.DataFrame({
            "period": series.index,
            "value": series.values,
            "trend": result.trend,
            "seasonal": result.seasonal,
            "residual": result.resid,
            "z_score": z_scores.values,
        })
        df["severity"] = df["z_score"].apply(_severity)
        df["metric"] = label
        df["anomaly_flag"] = (df["severity"] != "Normal").astype(int)
        return df
    except Exception as e:
        logger.warning(f"STL failed: {e}, falling back to rolling z-score")
        return rolling_zscore_anomalies(series, window=6, label=label)


def detect_all_anomalies(fact: pd.DataFrame) -> dict:
    """Run anomaly detection across all key metrics."""
    logger.info("Running anomaly detection...")

    # Build monthly series
    monthly = (
        fact.groupby("year_month_str")
        .agg(
            orders=("order_id", "count"),
            cancel_rate=("is_cancelled", "mean"),
            avg_shipping=("perkiraan_ongkir", "mean"),
            avg_payment=("total_pembayaran", "mean"),
            cod_rate=("is_cod", "mean"),
        )
        .reset_index()
        .sort_values("year_month_str")
    )
    monthly["cancel_rate"] = monthly["cancel_rate"] * 100
    monthly["cod_rate"] = monthly["cod_rate"] * 100

    def _to_series(df, col):
        s = pd.Series(df[col].values, index=df["year_month_str"].values)
        return s

    results = {}

    # 1. Order volume — STL decomposition
    results["order_volume"] = stl_residual_anomalies(
        _to_series(monthly, "orders"), label="monthly_order_volume"
    )

    # 2. Cancellation rate — rolling z-score
    results["cancellation_rate"] = rolling_zscore_anomalies(
        _to_series(monthly, "cancel_rate"), window=6, label="cancellation_rate_pct"
    )

    # 3. Shipping cost — IQR
    results["shipping_cost"] = iqr_anomalies(
        _to_series(monthly, "avg_shipping"), label="avg_shipping_cost"
    )

    # 4. Average payment — rolling z-score
    results["avg_payment"] = rolling_zscore_anomalies(
        _to_series(monthly, "avg_payment"), window=6, label="avg_payment_value"
    )

    # 5. Province-level anomaly: flag provinces with cancel_rate > 2 std above mean
    prov_cancel = (
        fact.groupby("province_clean")
        .agg(
            total=("order_id", "count"),
            cancel_rate=("is_cancelled", "mean"),
        )
        .reset_index()
    )
    prov_cancel["cancel_rate"] = prov_cancel["cancel_rate"] * 100
    mean_cr = prov_cancel["cancel_rate"].mean()
    std_cr = prov_cancel["cancel_rate"].std()
    prov_cancel["z_score"] = (prov_cancel["cancel_rate"] - mean_cr) / std_cr if std_cr > 0 else 0
    prov_cancel["severity"] = prov_cancel["z_score"].apply(_severity)
    prov_cancel["anomaly_flag"] = (prov_cancel["severity"] != "Normal").astype(int)
    results["province_cancellation"] = prov_cancel

    logger.info("Anomaly detection complete.")

    # Summary
    summary = {}
    for metric, df in results.items():
        if "severity" in df.columns:
            counts = df["severity"].value_counts().to_dict()
            flagged = int(df.get("anomaly_flag", pd.Series([0])).sum())
            summary[metric] = {"flagged_periods": flagged, "severity_counts": counts}

    return {"anomalies": results, "summary": summary}


def save_anomaly_report(result: dict, output_dir: str = REPORTS_PATH) -> str:
    """Save anomaly detection results."""
    os.makedirs(output_dir, exist_ok=True)

    for metric, df in result["anomalies"].items():
        if isinstance(df, pd.DataFrame):
            path = os.path.join(output_dir, f"anomaly_{metric}.parquet")
            df.to_parquet(path, index=False)

    summary_path = os.path.join(output_dir, "anomaly_report.json")
    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": result["summary"],
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Anomaly report saved: {summary_path}")
    return summary_path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
    fact = pd.read_parquet(os.path.join(MARTS_PATH, "fact_orders.parquet"))
    result = detect_all_anomalies(fact)
    save_anomaly_report(result)

    print("\nAnomaly Detection Summary:")
    for metric, info in result["summary"].items():
        print(f"  {metric}: {info['flagged_periods']} flagged periods | {info['severity_counts']}")

    print("\nOrder Volume Anomalies (non-normal):")
    ov = result["anomalies"]["order_volume"]
    flagged = ov[ov["anomaly_flag"] == 1]
    if len(flagged) > 0:
        print(flagged[["period", "value", "z_score", "severity"]].to_string(index=False))
    else:
        print("  No anomalies detected in order volume.")
