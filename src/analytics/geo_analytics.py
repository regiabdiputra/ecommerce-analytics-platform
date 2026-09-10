"""
Geographic Analytics module — province, city, and regional analysis.
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


def province_analysis(fact: pd.DataFrame) -> pd.DataFrame:
    """Full province-level performance metrics."""
    fact = fact.copy()
    fact["revenue_completed"] = fact["total_pembayaran"].where(fact["is_completed"] == 1, 0)
    prov = (
        fact.groupby(["province_clean", "region_group", "java_bali_flag"])
        .agg(
            total_orders=("order_id", "count"),
            completed_orders=("is_completed", "sum"),
            cancelled_orders=("is_cancelled", "sum"),
            total_revenue=("revenue_completed", "sum"),
            total_shipping=("perkiraan_ongkir", "sum"),
            avg_shipping=("perkiraan_ongkir", "mean"),
            avg_weight_kg=("weight_kg", "mean"),
            cod_orders=("is_cod", "sum"),
        )
        .reset_index()
        .sort_values("total_orders", ascending=False)
        .reset_index(drop=True)
    )
    prov["cancellation_rate"] = (
        prov["cancelled_orders"] / prov["total_orders"] * 100
    ).round(2)
    prov["completion_rate"] = (
        prov["completed_orders"] / prov["total_orders"] * 100
    ).round(2)
    prov["order_share_pct"] = (
        prov["total_orders"] / prov["total_orders"].sum() * 100
    ).round(2)
    prov["revenue_share_pct"] = (
        prov["total_revenue"] / prov["total_revenue"].sum() * 100
    ).round(2)
    prov["cod_rate"] = (
        prov["cod_orders"] / prov["total_orders"] * 100
    ).round(2)
    prov["avg_shipping"] = prov["avg_shipping"].round(0)
    prov["avg_weight_kg"] = prov["avg_weight_kg"].round(3)
    prov["cumulative_order_share"] = prov["order_share_pct"].cumsum().round(2)

    # Growth: first 12 months vs last 12 months
    fact_copy = fact.copy()
    fact_copy["period"] = fact_copy["year_month_str"].apply(
        lambda x: "early" if str(x) <= "2024-11" else "late"
    )
    growth = (
        fact_copy.groupby(["province_clean", "period"])["order_id"]
        .count()
        .unstack(fill_value=0)
        .reset_index()
    )
    if "early" in growth.columns and "late" in growth.columns:
        growth["growth_pct"] = (
            (growth["late"] - growth["early"]) /
            growth["early"].replace(0, np.nan) * 100
        ).round(2)
        prov = prov.merge(
            growth[["province_clean", "growth_pct"]], on="province_clean", how="left"
        )

    return prov


def city_analysis(fact: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    """Top N city/regency performance."""
    fact = fact.copy()
    fact["revenue_completed"] = fact["total_pembayaran"].where(fact["is_completed"] == 1, 0)
    city = (
        fact.groupby(["city_clean", "province_clean", "city_type"])
        .agg(
            total_orders=("order_id", "count"),
            completed_orders=("is_completed", "sum"),
            cancelled_orders=("is_cancelled", "sum"),
            total_revenue=("revenue_completed", "sum"),
            avg_shipping=("perkiraan_ongkir", "mean"),
        )
        .reset_index()
        .sort_values("total_orders", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    city["cancellation_rate"] = (
        city["cancelled_orders"] / city["total_orders"] * 100
    ).round(2)
    city["order_share_pct"] = (
        city["total_orders"] / fact.shape[0] * 100
    ).round(2)
    city["avg_shipping"] = city["avg_shipping"].round(0)
    return city


def region_group_analysis(fact: pd.DataFrame) -> pd.DataFrame:
    """Island group / region performance."""
    fact = fact.copy()
    fact["revenue_completed"] = fact["total_pembayaran"].where(fact["is_completed"] == 1, 0)
    region = (
        fact.groupby("region_group")
        .agg(
            total_orders=("order_id", "count"),
            completed_orders=("is_completed", "sum"),
            cancelled_orders=("is_cancelled", "sum"),
            total_revenue=("revenue_completed", "sum"),
            avg_shipping=("perkiraan_ongkir", "mean"),
            n_provinces=("province_clean", "nunique"),
        )
        .reset_index()
        .sort_values("total_orders", ascending=False)
    )
    region["cancellation_rate"] = (
        region["cancelled_orders"] / region["total_orders"] * 100
    ).round(2)
    region["order_share_pct"] = (
        region["total_orders"] / region["total_orders"].sum() * 100
    ).round(2)
    region["avg_shipping"] = region["avg_shipping"].round(0)
    return region


def geographic_risk_matrix(prov: pd.DataFrame) -> pd.DataFrame:
    """
    Classify provinces into risk/opportunity quadrants.
    Axes: order_share (volume) × cancellation_rate (risk)
    Quadrant:
      High Volume / Low Risk    → Core Market
      High Volume / High Risk   → Priority for Ops Improvement
      Low Volume / Low Risk     → Growth Opportunity
      Low Volume / High Risk    → Watch List
    """
    median_volume = prov["order_share_pct"].median()
    median_cancel = prov["cancellation_rate"].median()

    def _quadrant(row):
        hi_vol = row["order_share_pct"] >= median_volume
        hi_risk = row["cancellation_rate"] >= median_cancel
        if hi_vol and not hi_risk:
            return "Core Market"
        if hi_vol and hi_risk:
            return "Ops Priority"
        if not hi_vol and not hi_risk:
            return "Growth Opportunity"
        return "Watch List"

    prov = prov.copy()
    prov["quadrant"] = prov.apply(_quadrant, axis=1)
    return prov


def geographic_monthly_trend(fact: pd.DataFrame, top_provinces: int = 8) -> pd.DataFrame:
    """Monthly orders for top N provinces — for trend visualization."""
    top_prov = (
        fact.groupby("province_clean")
        .size()
        .nlargest(top_provinces)
        .index.tolist()
    )
    filtered = fact[fact["province_clean"].isin(top_prov)]
    trend = (
        filtered.groupby(["year_month_str", "province_clean"])
        .agg(orders=("order_id", "count"))
        .reset_index()
        .sort_values(["province_clean", "year_month_str"])
    )
    return trend


def run_geo_analytics(fact: pd.DataFrame) -> dict:
    """Run full geographic analytics suite."""
    logger.info("Running geographic analytics...")
    prov = province_analysis(fact)
    prov_with_quadrant = geographic_risk_matrix(prov)
    results = {
        "province": prov_with_quadrant,
        "city": city_analysis(fact),
        "region_group": region_group_analysis(fact),
        "monthly_trend_by_province": geographic_monthly_trend(fact),
    }
    logger.info("Geographic analytics complete.")
    return results


def save_geo_analytics(results: dict, output_dir: str = REPORTS_PATH) -> None:
    """Save geographic analytics results."""
    os.makedirs(output_dir, exist_ok=True)
    for name, data in results.items():
        if isinstance(data, pd.DataFrame):
            path = os.path.join(output_dir, f"geo_{name}.parquet")
            data.to_parquet(path, index=False)
            logger.info(f"  Saved geo_{name}: {len(data)} rows")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
    fact = pd.read_parquet(os.path.join(MARTS_PATH, "fact_orders.parquet"))
    results = run_geo_analytics(fact)
    save_geo_analytics(results)

    print("\nTop 10 Provinces:")
    print(results["province"].head(10)[
        ["province_clean", "total_orders", "order_share_pct",
         "cancellation_rate", "quadrant"]
    ].to_string(index=False))

    print("\nRegion Group Summary:")
    print(results["region_group"].to_string(index=False))
