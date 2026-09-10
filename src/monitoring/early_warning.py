"""
Early Warning System — rule-based alert engine for business monitoring.
Generates structured alerts with severity, evidence, and recommended actions.
"""
import pandas as pd
import numpy as np
import os
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MARTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "marts")
)
REPORTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports")
)


def _alert(metric, current_value, baseline_value, deviation_pct,
           severity, region_category, description, recommendation):
    """Build a standardized alert dict."""
    return {
        "metric": metric,
        "current_value": round(float(current_value), 2) if isinstance(current_value, float) else current_value,
        "baseline_value": round(float(baseline_value), 2) if isinstance(baseline_value, float) else baseline_value,
        "deviation_pct": round(float(deviation_pct), 2),
        "severity": severity,
        "affected": region_category,
        "description": description,
        "recommendation": recommendation,
        "timestamp": datetime.now().isoformat(),
    }


def check_cancellation_rate(fact: pd.DataFrame, alerts: list) -> None:
    """
    Alert if cancellation rate in most recent month is significantly above baseline.
    Baseline = mean of all prior months.
    """
    monthly = (
        fact.groupby("year_month_str")
        .agg(total=("order_id","count"), cancelled=("is_cancelled","sum"))
        .reset_index()
        .sort_values("year_month_str")
    )
    monthly["cancel_rate"] = monthly["cancelled"] / monthly["total"] * 100

    if len(monthly) < 4:
        return

    baseline = monthly.iloc[:-1]["cancel_rate"].mean()
    current = monthly.iloc[-1]["cancel_rate"]
    current_month = monthly.iloc[-1]["year_month_str"]
    deviation = (current - baseline) / baseline * 100 if baseline > 0 else 0

    if abs(deviation) >= 50:
        severity = "Critical"
    elif abs(deviation) >= 25:
        severity = "Warning"
    elif abs(deviation) >= 15:
        severity = "Watch"
    else:
        return  # No alert needed

    alerts.append(_alert(
        metric="cancellation_rate",
        current_value=current,
        baseline_value=baseline,
        deviation_pct=deviation,
        severity=severity,
        region_category=f"All orders — {current_month}",
        description=f"Cancellation rate in {current_month} is {current:.1f}% vs baseline {baseline:.1f}%.",
        recommendation="Investigate recent cancellation reasons. Check if COD-related or system-related "
                       "cancellations increased. Review operational processes.",
    ))


def check_order_volume_decline(fact: pd.DataFrame, alerts: list) -> None:
    """Alert on significant MoM order volume decline in recent months."""
    monthly = (
        fact.groupby("year_month_str")
        .agg(orders=("order_id","count"))
        .reset_index()
        .sort_values("year_month_str")
    )

    if len(monthly) < 3:
        return

    # Check last 3 months for consecutive decline
    last3 = monthly.tail(3)
    orders = last3["orders"].values
    months = last3["year_month_str"].values

    # MoM change in last month
    if len(orders) >= 2:
        current = orders[-1]
        prior = orders[-2]
        mom_pct = (current - prior) / prior * 100 if prior > 0 else 0

        # Rolling 6-month baseline
        baseline = monthly.iloc[-7:-1]["orders"].mean() if len(monthly) >= 7 else monthly.iloc[:-1]["orders"].mean()
        baseline_dev = (current - baseline) / baseline * 100 if baseline > 0 else 0

        if mom_pct <= -25:
            severity = "Critical"
        elif mom_pct <= -15:
            severity = "Warning"
        elif mom_pct <= -10:
            severity = "Watch"
        else:
            return

        alerts.append(_alert(
            metric="order_volume",
            current_value=int(current),
            baseline_value=round(float(baseline), 0),
            deviation_pct=baseline_dev,
            severity=severity,
            region_category=f"All orders — {months[-1]}",
            description=f"Order volume in {months[-1]} is {current:,} orders ({mom_pct:+.1f}% MoM). "
                        f"Baseline (6-month avg): {baseline:.0f}.",
            recommendation="Investigate external factors (platform changes, competition, seasonality). "
                           "Review marketing spend and promotions. Requires operational investigation.",
        ))


def check_regional_volume_decline(fact: pd.DataFrame, alerts: list, top_n: int = 5) -> None:
    """Alert on significant volume decline in top provinces."""
    # Get top N provinces by total orders
    top_provinces = (
        fact.groupby("province_clean")["order_id"].count()
        .nlargest(top_n).index.tolist()
    )

    for province in top_provinces:
        prov_data = fact[fact["province_clean"] == province]
        monthly = (
            prov_data.groupby("year_month_str")
            .agg(orders=("order_id","count"))
            .reset_index()
            .sort_values("year_month_str")
        )
        if len(monthly) < 4:
            continue

        baseline = monthly.iloc[:-1]["orders"].mean()
        current = monthly.iloc[-1]["orders"]
        current_month = monthly.iloc[-1]["year_month_str"]
        deviation = (current - baseline) / baseline * 100 if baseline > 0 else 0

        if deviation <= -30:
            severity = "Warning"
            alerts.append(_alert(
                metric="regional_order_volume",
                current_value=int(current),
                baseline_value=round(float(baseline), 0),
                deviation_pct=deviation,
                severity=severity,
                region_category=province,
                description=f"{province}: {current:,} orders in {current_month} "
                            f"vs baseline {baseline:.0f} ({deviation:+.1f}%).",
                recommendation=f"Investigate performance decline in {province}. "
                               "Check regional competition, logistics issues, or demand shifts. "
                               "Requires operational investigation.",
            ))


def check_shipping_cost_spike(fact: pd.DataFrame, alerts: list) -> None:
    """Alert on unusual shipping cost increase."""
    monthly = (
        fact.groupby("year_month_str")
        .agg(avg_shipping=("perkiraan_ongkir","mean"))
        .reset_index()
        .sort_values("year_month_str")
    )

    if len(monthly) < 4:
        return

    baseline = monthly.iloc[:-1]["avg_shipping"].mean()
    current = monthly.iloc[-1]["avg_shipping"]
    current_month = monthly.iloc[-1]["year_month_str"]
    deviation = (current - baseline) / baseline * 100 if baseline > 0 else 0

    if deviation >= 25:
        severity = "Warning"
        alerts.append(_alert(
            metric="avg_shipping_cost",
            current_value=round(float(current), 0),
            baseline_value=round(float(baseline), 0),
            deviation_pct=deviation,
            severity=severity,
            region_category=f"All orders — {current_month}",
            description=f"Average shipping cost in {current_month}: Rp {current:,.0f} "
                        f"(+{deviation:.1f}% above baseline Rp {baseline:,.0f}).",
            recommendation="Review shipping carrier rate changes. Check if order weight mix "
                           "has shifted toward heavier categories. Requires operational investigation.",
        ))


def check_cod_cancellation_spike(fact: pd.DataFrame, alerts: list) -> None:
    """Alert if COD cancellation rate significantly exceeds non-COD cancellation rate."""
    cod = fact[fact["is_cod"] == 1]
    non_cod = fact[fact["is_cod"] == 0]

    cod_cancel_rate = cod["is_cancelled"].mean() * 100 if len(cod) > 0 else 0
    non_cod_cancel_rate = non_cod["is_cancelled"].mean() * 100 if len(non_cod) > 0 else 0
    gap = cod_cancel_rate - non_cod_cancel_rate

    if gap >= 10:
        severity = "Warning" if gap >= 15 else "Watch"
        alerts.append(_alert(
            metric="cod_vs_digital_cancellation_gap",
            current_value=cod_cancel_rate,
            baseline_value=non_cod_cancel_rate,
            deviation_pct=gap,
            severity=severity,
            region_category="COD orders vs Digital payment orders",
            description=f"COD cancellation rate ({cod_cancel_rate:.1f}%) exceeds "
                        f"digital payment cancellation rate ({non_cod_cancel_rate:.1f}%) "
                        f"by {gap:.1f} percentage points.",
            recommendation="Consider implementing COD verification steps, minimum order value for COD, "
                           "or region-specific COD restrictions for high-risk areas.",
        ))


def check_high_risk_provinces(fact: pd.DataFrame, alerts: list) -> None:
    """Alert on provinces with cancellation rate significantly above average."""
    prov = (
        fact.groupby("province_clean")
        .agg(total=("order_id","count"), cancelled=("is_cancelled","sum"))
        .reset_index()
    )
    prov["cancel_rate"] = prov["cancelled"] / prov["total"] * 100
    # Only consider provinces with meaningful volume (>= 50 orders)
    prov = prov[prov["total"] >= 50]

    overall_mean = prov["cancel_rate"].mean()
    overall_std = prov["cancel_rate"].std()
    threshold = overall_mean + 1.5 * overall_std

    high_risk = prov[prov["cancel_rate"] >= threshold].sort_values("cancel_rate", ascending=False)

    for _, row in high_risk.iterrows():
        deviation = (row["cancel_rate"] - overall_mean) / overall_mean * 100
        severity = "Critical" if row["cancel_rate"] >= overall_mean + 2 * overall_std else "Warning"
        alerts.append(_alert(
            metric="province_cancellation_rate",
            current_value=row["cancel_rate"],
            baseline_value=overall_mean,
            deviation_pct=deviation,
            severity=severity,
            region_category=row["province_clean"],
            description=f"{row['province_clean']}: cancellation rate {row['cancel_rate']:.1f}% "
                        f"(national avg: {overall_mean:.1f}%, {row['total']:,} orders).",
            recommendation=f"Investigate cancellation drivers in {row['province_clean']}. "
                           "Check if COD proportion is high, logistics reliability, or buyer quality issues. "
                           "Requires operational investigation.",
        ))


def run_early_warning(fact: pd.DataFrame) -> dict:
    """Run all early warning checks and return structured alert list."""
    logger.info("Running early warning system...")
    alerts = []

    check_cancellation_rate(fact, alerts)
    check_order_volume_decline(fact, alerts)
    check_regional_volume_decline(fact, alerts)
    check_shipping_cost_spike(fact, alerts)
    check_cod_cancellation_spike(fact, alerts)
    check_high_risk_provinces(fact, alerts)

    # Sort by severity
    severity_order = {"Critical": 0, "Warning": 1, "Watch": 2, "Normal": 3}
    alerts.sort(key=lambda x: severity_order.get(x["severity"], 4))

    summary = {
        "total_alerts": len(alerts),
        "critical": sum(1 for a in alerts if a["severity"] == "Critical"),
        "warning": sum(1 for a in alerts if a["severity"] == "Warning"),
        "watch": sum(1 for a in alerts if a["severity"] == "Watch"),
    }

    logger.info(f"Early warning complete: {summary}")
    return {"alerts": alerts, "summary": summary}


def save_early_warning(result: dict, output_dir: str = REPORTS_PATH) -> str:
    """Save early warning alerts to JSON."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "early_warning_alerts.json")
    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": result["summary"],
        "alerts": result["alerts"],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Early warning report saved: {path}")
    return path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
    fact = pd.read_parquet(os.path.join(MARTS_PATH, "fact_orders.parquet"))
    result = run_early_warning(fact)
    save_early_warning(result)

    print(f"\nEarly Warning Summary: {result['summary']}")
    print("\nAlerts:")
    for alert in result["alerts"]:
        print(f"\n  [{alert['severity']}] {alert['metric']} — {alert['affected']}")
        print(f"    Current: {alert['current_value']} | Baseline: {alert['baseline_value']} "
              f"| Deviation: {alert['deviation_pct']:+.1f}%")
        print(f"    {alert['description']}")
        print(f"    → {alert['recommendation']}")
