"""
Operations Analytics module — cancellation, shipping, and operational analysis.
"""
import pandas as pd
import numpy as np
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MARTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "marts")
)
REPORTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports")
)


def cancellation_analysis(fact: pd.DataFrame) -> dict:
    """Full cancellation pattern analysis."""
    cancelled = fact[fact["is_cancelled"] == 1].copy()

    # By reason
    by_reason = (
        cancelled.groupby("cancellation_reason_clean")
        .agg(count=("order_id", "count"))
        .reset_index()
        .sort_values("count", ascending=False)
    )
    by_reason["pct"] = (by_reason["count"] / len(cancelled) * 100).round(2)

    # By initiator
    by_initiator = (
        cancelled.groupby("cancellation_initiator")
        .agg(count=("order_id", "count"))
        .reset_index()
        .sort_values("count", ascending=False)
    )
    by_initiator["pct"] = (by_initiator["count"] / len(cancelled) * 100).round(2)

    # By payment method
    by_payment = (
        fact.groupby("metode_pembayaran")
        .agg(
            total=("order_id", "count"),
            cancelled=("is_cancelled", "sum"),
        )
        .reset_index()
    )
    by_payment["cancel_rate"] = (by_payment["cancelled"] / by_payment["total"] * 100).round(2)
    by_payment = by_payment.sort_values("cancel_rate", ascending=False)

    # By province
    by_province = (
        fact.groupby("province_clean")
        .agg(
            total=("order_id", "count"),
            cancelled=("is_cancelled", "sum"),
        )
        .reset_index()
    )
    by_province["cancel_rate"] = (by_province["cancelled"] / by_province["total"] * 100).round(2)
    by_province = by_province.sort_values("cancel_rate", ascending=False)

    # Monthly cancellation trend
    monthly_cancel = (
        fact.groupby("year_month_str")
        .agg(
            total=("order_id", "count"),
            cancelled=("is_cancelled", "sum"),
        )
        .reset_index()
        .sort_values("year_month_str")
    )
    monthly_cancel["cancel_rate"] = (
        monthly_cancel["cancelled"] / monthly_cancel["total"] * 100
    ).round(2)
    monthly_cancel["cancel_rate_3m_avg"] = (
        monthly_cancel["cancel_rate"].rolling(3, min_periods=1).mean()
    ).round(2)

    # COD vs non-COD cancellation
    cod_cancel = float(fact[fact["is_cod"] == 1]["is_cancelled"].mean() * 100)
    non_cod_cancel = float(fact[fact["is_cod"] == 0]["is_cancelled"].mean() * 100)

    return {
        "total_cancelled": int(len(cancelled)),
        "overall_cancel_rate": round(len(cancelled) / len(fact) * 100, 2),
        "by_reason": by_reason,
        "by_initiator": by_initiator,
        "by_payment": by_payment,
        "by_province": by_province,
        "monthly_trend": monthly_cancel,
        "cod_cancel_rate": round(cod_cancel, 2),
        "non_cod_cancel_rate": round(non_cod_cancel, 2),
    }


def shipping_analysis(fact: pd.DataFrame) -> dict:
    """Shipping cost and weight analysis."""

    # By tier
    by_tier = (
        fact.groupby("shipping_tier")
        .agg(
            total_orders=("order_id", "count"),
            avg_shipping_cost=("perkiraan_ongkir", "mean"),
            avg_weight_kg=("weight_kg", "mean"),
            avg_subsidy=("estimasi_potongan_ongkir", "mean"),
            cancel_rate=("is_cancelled", "mean"),
        )
        .reset_index()
        .sort_values("total_orders", ascending=False)
    )
    by_tier["cancel_rate"] = (by_tier["cancel_rate"] * 100).round(2)
    by_tier["avg_shipping_cost"] = by_tier["avg_shipping_cost"].round(0)
    by_tier["avg_weight_kg"] = by_tier["avg_weight_kg"].round(3)
    by_tier["order_share_pct"] = (
        by_tier["total_orders"] / by_tier["total_orders"].sum() * 100
    ).round(2)

    # By courier
    by_courier = (
        fact.groupby("shipping_courier")
        .agg(
            total_orders=("order_id", "count"),
            avg_shipping_cost=("perkiraan_ongkir", "mean"),
            cancel_rate=("is_cancelled", "mean"),
        )
        .reset_index()
        .sort_values("total_orders", ascending=False)
    )
    by_courier["cancel_rate"] = (by_courier["cancel_rate"] * 100).round(2)
    by_courier["avg_shipping_cost"] = by_courier["avg_shipping_cost"].round(0)

    # Weight distribution
    completed = fact[fact["is_completed"] == 1]
    weight_stats = {
        "min_kg": round(float(completed["weight_kg"].min()), 3),
        "p25_kg": round(float(completed["weight_kg"].quantile(0.25)), 3),
        "median_kg": round(float(completed["weight_kg"].median()), 3),
        "p75_kg": round(float(completed["weight_kg"].quantile(0.75)), 3),
        "p95_kg": round(float(completed["weight_kg"].quantile(0.95)), 3),
        "p99_kg": round(float(completed["weight_kg"].quantile(0.99)), 3),
        "max_kg": round(float(completed["weight_kg"].max()), 3),
        "mean_kg": round(float(completed["weight_kg"].mean()), 3),
    }

    # Shipping cost vs weight correlation (completed orders)
    corr = float(completed["weight_kg"].corr(completed["perkiraan_ongkir"]))

    # Monthly shipping cost trend
    monthly_shipping = (
        fact.groupby("year_month_str")
        .agg(
            avg_shipping_cost=("perkiraan_ongkir", "mean"),
            total_shipping_cost=("perkiraan_ongkir", "sum"),
            avg_weight_kg=("weight_kg", "mean"),
            free_shipping_rate=("is_free_shipping", "mean"),
        )
        .reset_index()
        .sort_values("year_month_str")
    )
    monthly_shipping["free_shipping_rate"] = (
        monthly_shipping["free_shipping_rate"] * 100
    ).round(2)

    # By province — avg shipping cost
    by_province = (
        fact.groupby("province_clean")
        .agg(
            avg_shipping=("perkiraan_ongkir", "mean"),
            avg_weight_kg=("weight_kg", "mean"),
            total_orders=("order_id", "count"),
        )
        .reset_index()
        .sort_values("avg_shipping", ascending=False)
    )
    by_province["avg_shipping"] = by_province["avg_shipping"].round(0)

    return {
        "by_tier": by_tier,
        "by_courier": by_courier,
        "weight_distribution": weight_stats,
        "weight_shipping_correlation": round(corr, 4),
        "monthly_trend": monthly_shipping,
        "by_province": by_province,
    }


def operational_summary(fact: pd.DataFrame) -> dict:
    """High-level operational health summary."""
    total = len(fact)
    completed = int(fact["is_completed"].sum())
    cancelled = int(fact["is_cancelled"].sum())
    in_transit = int((fact["status_normalized"] == "in_transit").sum())

    # Free shipping dominance
    free_ship = int(fact["is_free_shipping"].sum())

    # Subsidy dependency
    avg_subsidy_pct = float(fact["shipping_subsidy_ratio"].mean() * 100)

    # Bulk orders
    bulk = int(fact["is_bulk_order"].sum())

    # Return rate
    returned = int(fact["is_returned"].sum())

    return {
        "total_orders": total,
        "completed": completed,
        "cancelled": cancelled,
        "in_transit": in_transit,
        "completion_rate_pct": round(completed / total * 100, 2),
        "cancellation_rate_pct": round(cancelled / total * 100, 2),
        "free_shipping_pct": round(free_ship / total * 100, 2),
        "avg_platform_subsidy_pct": round(avg_subsidy_pct, 2),
        "bulk_orders": bulk,
        "bulk_order_pct": round(bulk / total * 100, 2),
        "returned_orders": returned,
        "return_rate_pct": round(returned / total * 100, 4),
        "delivery_sla_available": False,
        "delivery_sla_note": "Delivery timestamp not available in dataset — SLA analysis not possible.",
    }


def run_operations_analytics(fact: pd.DataFrame) -> dict:
    """Run full operations analytics suite."""
    logger.info("Running operations analytics...")
    results = {
        "cancellation": cancellation_analysis(fact),
        "shipping": shipping_analysis(fact),
        "summary": operational_summary(fact),
    }
    logger.info("Operations analytics complete.")
    return results


def save_operations_analytics(results: dict, output_dir: str = REPORTS_PATH) -> None:
    """Save operations analytics results."""
    os.makedirs(output_dir, exist_ok=True)
    summary = {
        k: v for k, v in results.items()
        if not isinstance(v, pd.DataFrame)
    }
    # Flatten DataFrames from nested dicts
    for section_name, section in results.items():
        if isinstance(section, dict):
            for key, val in section.items():
                if isinstance(val, pd.DataFrame):
                    path = os.path.join(output_dir, f"ops_{section_name}_{key}.parquet")
                    val.to_parquet(path, index=False)
        elif isinstance(section, pd.DataFrame):
            path = os.path.join(output_dir, f"ops_{section_name}.parquet")
            section.to_parquet(path, index=False)

    path = os.path.join(output_dir, "ops_summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results["summary"], f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Operations summary saved: {path}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
    fact = pd.read_parquet(os.path.join(MARTS_PATH, "fact_orders.parquet"))
    results = run_operations_analytics(fact)
    save_operations_analytics(results)

    print("\nOperational Summary:")
    for k, v in results["summary"].items():
        print(f"  {k}: {v}")

    print("\nCancellation by Reason:")
    print(results["cancellation"]["by_reason"].to_string(index=False))

    print("\nShipping by Tier:")
    print(results["shipping"]["by_tier"][
        ["shipping_tier", "total_orders", "order_share_pct", "avg_shipping_cost"]
    ].to_string(index=False))
