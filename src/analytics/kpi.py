"""
KPI layer — defines and computes all business KPIs from the fact table.
Every KPI has explicit formula, grain, and business meaning documented.
Output: outputs/reports/kpi_summary.json
"""
import pandas as pd
import numpy as np
import json
import os
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


def load_fact(marts_path: str = MARTS_PATH) -> pd.DataFrame:
    return pd.read_parquet(os.path.join(marts_path, "fact_orders.parquet"))


def compute_kpis(fact: pd.DataFrame) -> dict:
    """
    Compute all KPIs from fact_orders.
    Returns structured dict with KPI values, formulas, and metadata.
    """
    kpis = {}

    # ── SALES KPIs ─────────────────────────────────────────────────────────────

    # KPI-01: Total Orders
    kpis["total_orders"] = {
        "value": int(len(fact)),
        "formula": "COUNT(order_id)",
        "grain": "all-time",
        "unit": "orders",
        "business_meaning": "Total number of orders placed across the entire dataset period.",
    }

    # KPI-02: Completed Orders
    n_completed = int(fact["is_completed"].sum())
    kpis["completed_orders"] = {
        "value": n_completed,
        "formula": "COUNT(order_id) WHERE is_completed = 1",
        "grain": "all-time",
        "unit": "orders",
        "business_meaning": "Orders that reached completed or completed_review status.",
    }

    # KPI-03: Cancelled Orders
    n_cancelled = int(fact["is_cancelled"].sum())
    kpis["cancelled_orders"] = {
        "value": n_cancelled,
        "formula": "COUNT(order_id) WHERE is_cancelled = 1",
        "grain": "all-time",
        "unit": "orders",
        "business_meaning": "Orders that were cancelled by buyer, system, or seller.",
    }

    # KPI-04: Cancellation Rate
    cancel_rate = n_cancelled / len(fact) * 100
    kpis["cancellation_rate"] = {
        "value": round(cancel_rate, 2),
        "formula": "cancelled_orders / total_orders * 100",
        "grain": "all-time",
        "unit": "%",
        "business_meaning": "Percentage of all orders that were cancelled.",
    }

    # KPI-05: Total Quantity Sold (completed orders only)
    total_qty = int(fact.loc[fact["is_completed"] == 1, "total_qty"].sum())
    kpis["total_quantity_sold"] = {
        "value": total_qty,
        "formula": "SUM(total_qty) WHERE is_completed = 1",
        "grain": "all-time",
        "unit": "units",
        "business_meaning": "Total number of product units in completed orders.",
    }

    # KPI-06: Total Revenue (Total Pembayaran — completed orders)
    total_revenue = int(fact.loc[fact["is_completed"] == 1, "total_pembayaran"].sum())
    kpis["total_revenue"] = {
        "value": total_revenue,
        "formula": "SUM(total_pembayaran) WHERE is_completed = 1",
        "grain": "all-time",
        "unit": "IDR",
        "business_meaning": "Total buyer payment collected from completed orders. "
                            "Does not include platform fees or COGS (not available).",
    }

    # KPI-07: Average Order Value (completed orders)
    aov = total_revenue / n_completed if n_completed > 0 else 0
    kpis["avg_order_value"] = {
        "value": round(aov, 2),
        "formula": "total_revenue / completed_orders",
        "grain": "all-time",
        "unit": "IDR",
        "business_meaning": "Average buyer payment per completed order.",
    }

    # KPI-08: Median Order Value
    median_ov = float(fact.loc[fact["is_completed"] == 1, "total_pembayaran"].median())
    kpis["median_order_value"] = {
        "value": round(median_ov, 2),
        "formula": "MEDIAN(total_pembayaran) WHERE is_completed = 1",
        "grain": "all-time",
        "unit": "IDR",
        "business_meaning": "Median buyer payment — more robust to outlier bulk orders than AOV.",
    }

    # ── OPERATIONS KPIs ────────────────────────────────────────────────────────

    # KPI-09: Total Shipping Cost (all orders — perkiraan_ongkir)
    total_shipping = int(fact["perkiraan_ongkir"].sum())
    kpis["total_shipping_cost"] = {
        "value": total_shipping,
        "formula": "SUM(perkiraan_ongkir)",
        "grain": "all-time",
        "unit": "IDR",
        "business_meaning": "Total estimated shipping cost across all orders.",
    }

    # KPI-10: Average Shipping Cost per Order
    avg_shipping = float(fact["perkiraan_ongkir"].mean())
    kpis["avg_shipping_cost"] = {
        "value": round(avg_shipping, 2),
        "formula": "AVG(perkiraan_ongkir)",
        "grain": "all-time",
        "unit": "IDR",
        "business_meaning": "Average full shipping cost per order (before subsidies).",
    }

    # KPI-11: Total Shipping Subsidy
    total_subsidy = int(fact["estimasi_potongan_ongkir"].sum())
    kpis["total_shipping_subsidy"] = {
        "value": total_subsidy,
        "formula": "SUM(estimasi_potongan_ongkir)",
        "grain": "all-time",
        "unit": "IDR",
        "business_meaning": "Total shipping cost absorbed by platform as subsidy.",
    }

    # KPI-12: Average Shipping Subsidy Rate
    avg_subsidy_rate = float(fact["shipping_subsidy_ratio"].mean()) * 100
    kpis["avg_shipping_subsidy_rate"] = {
        "value": round(avg_subsidy_rate, 2),
        "formula": "AVG(estimasi_potongan_ongkir / perkiraan_ongkir) * 100",
        "grain": "all-time",
        "unit": "%",
        "business_meaning": "Average percentage of shipping cost covered by platform subsidy.",
    }

    # KPI-13: Free Shipping Rate
    free_ship_rate = float(fact["is_free_shipping"].mean()) * 100
    kpis["free_shipping_rate"] = {
        "value": round(free_ship_rate, 2),
        "formula": "COUNT(ongkir_dibayar_pembeli = 0) / total_orders * 100",
        "grain": "all-time",
        "unit": "%",
        "business_meaning": "Percentage of orders where buyer paid zero shipping fee.",
    }

    # KPI-14: Average Shipment Weight
    avg_weight_kg = float(fact["weight_kg"].mean())
    kpis["avg_shipment_weight_kg"] = {
        "value": round(avg_weight_kg, 3),
        "formula": "AVG(total_weight_gr / 1000)",
        "grain": "all-time",
        "unit": "kg",
        "business_meaning": "Average shipment weight per order.",
    }

    # KPI-15: COD Rate
    cod_rate = float(fact["is_cod"].mean()) * 100
    kpis["cod_rate"] = {
        "value": round(cod_rate, 2),
        "formula": "COUNT(is_cod = 1) / total_orders * 100",
        "grain": "all-time",
        "unit": "%",
        "business_meaning": "Percentage of orders paid via Cash on Delivery. "
                            "High COD rate increases operational risk of delivery cancellation.",
    }

    # KPI-16: COD Cancellation Rate
    cod_orders = fact[fact["is_cod"] == 1]
    cod_cancel_rate = float(cod_orders["is_cancelled"].mean()) * 100 if len(cod_orders) > 0 else 0
    non_cod_orders = fact[fact["is_cod"] == 0]
    non_cod_cancel_rate = float(non_cod_orders["is_cancelled"].mean()) * 100 if len(non_cod_orders) > 0 else 0
    kpis["cod_cancellation_rate"] = {
        "value": round(cod_cancel_rate, 2),
        "formula": "COUNT(cancelled AND is_cod=1) / COUNT(is_cod=1) * 100",
        "grain": "all-time",
        "unit": "%",
        "business_meaning": "Cancellation rate for COD orders specifically.",
        "non_cod_cancellation_rate": round(non_cod_cancel_rate, 2),
    }

    # ── COMMERCIAL KPIs ────────────────────────────────────────────────────────

    # KPI-17: Discount Rate (orders with any discount)
    discount_rate = float(fact["has_discount"].mean()) * 100
    kpis["discount_rate"] = {
        "value": round(discount_rate, 2),
        "formula": "COUNT(has_discount = 1) / total_orders * 100",
        "grain": "all-time",
        "unit": "%",
        "business_meaning": "Percentage of orders that had any discount applied.",
    }

    # KPI-18: Top Province by Orders
    top_province = fact.groupby("province_clean").size().idxmax()
    top_province_pct = float(
        fact.groupby("province_clean").size().max() / len(fact) * 100
    )
    kpis["top_province"] = {
        "value": top_province,
        "pct_of_total": round(top_province_pct, 2),
        "formula": "province with MAX(COUNT(order_id))",
        "grain": "all-time",
        "unit": "province name",
        "business_meaning": "Province contributing the most orders.",
    }

    # KPI-19: Java-Bali Concentration
    java_bali_pct = float(fact["java_bali_flag"].mean()) * 100
    kpis["java_bali_concentration"] = {
        "value": round(java_bali_pct, 2),
        "formula": "COUNT(java_bali_flag = 1) / total_orders * 100",
        "grain": "all-time",
        "unit": "%",
        "business_meaning": "Percentage of orders from Java, Bali, and Banten provinces.",
    }

    # KPI-20: Multi-category order rate
    multi_cat_rate = float(fact["is_multi_category"].mean()) * 100
    kpis["multi_category_rate"] = {
        "value": round(multi_cat_rate, 2),
        "formula": "COUNT(num_product_categories > 1) / total_orders * 100",
        "grain": "all-time",
        "unit": "%",
        "business_meaning": "Percentage of orders containing items from multiple product categories.",
    }

    return kpis


def compute_monthly_kpis(fact: pd.DataFrame) -> pd.DataFrame:
    """
    Compute KPIs aggregated by year_month_str.
    Returns DataFrame suitable for time-series analysis and MoM calculations.
    """
    fact = fact.copy()
    fact["revenue_completed"] = fact["total_pembayaran"].where(fact["is_completed"] == 1, 0)
    monthly = (
        fact.groupby("year_month_str")
        .agg(
            total_orders=("order_id", "count"),
            completed_orders=("is_completed", "sum"),
            cancelled_orders=("is_cancelled", "sum"),
            total_qty=("total_qty", "sum"),
            total_revenue=("revenue_completed", "sum"),
            total_shipping_cost=("perkiraan_ongkir", "sum"),
            total_subsidy=("estimasi_potongan_ongkir", "sum"),
            avg_weight_kg=("weight_kg", "mean"),
            cod_orders=("is_cod", "sum"),
            free_shipping_orders=("is_free_shipping", "sum"),
        )
        .reset_index()
        .sort_values("year_month_str")
    )
    monthly["avg_order_value"] = (
        monthly["total_revenue"] / monthly["completed_orders"].replace(0, np.nan)
    ).round(2)

    # Derived monthly KPIs
    monthly["cancellation_rate"] = (
        monthly["cancelled_orders"] / monthly["total_orders"] * 100
    ).round(2)
    monthly["completion_rate"] = (
        monthly["completed_orders"] / monthly["total_orders"] * 100
    ).round(2)
    monthly["cod_rate"] = (
        monthly["cod_orders"] / monthly["total_orders"] * 100
    ).round(2)
    monthly["free_shipping_rate"] = (
        monthly["free_shipping_orders"] / monthly["total_orders"] * 100
    ).round(2)
    monthly["subsidy_rate"] = (
        monthly["total_subsidy"] / monthly["total_shipping_cost"] * 100
    ).round(2)

    # MoM Growth (orders)
    monthly["orders_mom_growth"] = (
        monthly["total_orders"].pct_change() * 100
    ).round(2)

    # MoM Growth (revenue)
    monthly["revenue_mom_growth"] = (
        monthly["total_revenue"].pct_change() * 100
    ).round(2)

    # Rolling 3-month average (orders)
    monthly["orders_3m_avg"] = (
        monthly["total_orders"].rolling(3, min_periods=1).mean()
    ).round(1)

    return monthly


def compute_category_kpis(fact: pd.DataFrame, df_cats: pd.DataFrame) -> pd.DataFrame:
    """Compute KPIs by product category using exploded category data."""
    df_cats = df_cats.copy()
    df_cats["revenue_completed"] = df_cats["total_pembayaran"].where(df_cats["is_completed"] == 1, 0)
    cat_kpis = (
        df_cats.groupby("category")
        .agg(
            total_orders=("order_id", "count"),
            completed_orders=("is_completed", "sum"),
            cancelled_orders=("is_cancelled", "sum"),
            total_qty=("total_qty", "sum"),
            total_revenue=("revenue_completed", "sum"),
        )
        .reset_index()
        .sort_values("total_orders", ascending=False)
    )
    cat_kpis["cancellation_rate"] = (
        cat_kpis["cancelled_orders"] / cat_kpis["total_orders"] * 100
    ).round(2)
    cat_kpis["order_share_pct"] = (
        cat_kpis["total_orders"] / cat_kpis["total_orders"].sum() * 100
    ).round(2)
    # Pareto cumulative share
    cat_kpis["cumulative_order_share"] = cat_kpis["order_share_pct"].cumsum().round(2)

    return cat_kpis


def compute_geo_kpis(fact: pd.DataFrame) -> pd.DataFrame:
    """Compute KPIs by province."""
    fact = fact.copy()
    fact["revenue_completed"] = fact["total_pembayaran"].where(fact["is_completed"] == 1, 0)
    geo_kpis = (
        fact.groupby("province_clean")
        .agg(
            total_orders=("order_id", "count"),
            completed_orders=("is_completed", "sum"),
            cancelled_orders=("is_cancelled", "sum"),
            total_revenue=("revenue_completed", "sum"),
            total_shipping=("perkiraan_ongkir", "sum"),
            avg_weight_kg=("weight_kg", "mean"),
        )
        .reset_index()
        .sort_values("total_orders", ascending=False)
    )
    geo_kpis["cancellation_rate"] = (
        geo_kpis["cancelled_orders"] / geo_kpis["total_orders"] * 100
    ).round(2)
    geo_kpis["order_share_pct"] = (
        geo_kpis["total_orders"] / geo_kpis["total_orders"].sum() * 100
    ).round(2)
    geo_kpis["avg_shipping_per_order"] = (
        geo_kpis["total_shipping"] / geo_kpis["total_orders"]
    ).round(0)

    return geo_kpis


def save_kpi_report(kpis: dict, monthly: pd.DataFrame,
                    output_dir: str = REPORTS_PATH) -> str:
    """Save KPI summary to JSON."""
    os.makedirs(output_dir, exist_ok=True)
    report = {
        "generated_at": datetime.now().isoformat(),
        "overall_kpis": kpis,
        "monthly_kpis": monthly.to_dict(orient="records"),
    }
    path = os.path.join(output_dir, "kpi_summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"KPI report saved: {path}")
    return path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))

    fact = load_fact()
    df_cats = pd.read_parquet(
        os.path.join(MARTS_PATH.replace("marts", "processed"), "orders_categories.parquet")
    )

    kpis = compute_kpis(fact)
    monthly = compute_monthly_kpis(fact)
    cat_kpis = compute_category_kpis(fact, df_cats)
    geo_kpis = compute_geo_kpis(fact)

    save_kpi_report(kpis, monthly)

    print("\n" + "=" * 60)
    print("  OVERALL KPI SUMMARY")
    print("=" * 60)
    for name, kpi in kpis.items():
        val = kpi["value"]
        unit = kpi.get("unit", "")
        if unit == "IDR" and isinstance(val, (int, float)):
            val_str = f"Rp {val:,.0f}"
        elif unit == "%":
            val_str = f"{val:.2f}%"
        elif isinstance(val, (int, float)):
            val_str = f"{val:,.2f}"
        else:
            val_str = str(val)
        print(f"  {name:<40} {val_str}")

    print("\n  Monthly KPIs (last 6 months):")
    print(monthly.tail(6)[["year_month_str", "total_orders", "cancellation_rate",
                             "orders_mom_growth"]].to_string(index=False))

    print("\n  Top 10 Categories:")
    print(cat_kpis.head(10)[["category", "total_orders", "order_share_pct",
                               "cancellation_rate"]].to_string(index=False))
