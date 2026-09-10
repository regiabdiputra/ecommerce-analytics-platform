"""
Sales Analytics module — comprehensive sales performance analysis.
Analyzes trends, categories, regions, payment, and growth patterns.
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
PROCESSED_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
)
REPORTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports")
)


def monthly_sales_trend(fact: pd.DataFrame) -> pd.DataFrame:
    """Monthly order volume, revenue, and growth metrics."""
    # Pre-compute revenue only for completed orders (0 for cancelled)
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
            total_shipping=("perkiraan_ongkir", "sum"),
        )
        .reset_index()
        .sort_values("year_month_str")
    )
    monthly["cancellation_rate"] = (
        monthly["cancelled_orders"] / monthly["total_orders"] * 100
    ).round(2)
    monthly["orders_mom_pct"] = monthly["total_orders"].pct_change().mul(100).round(2)
    monthly["revenue_mom_pct"] = monthly["total_revenue"].pct_change().mul(100).round(2)
    monthly["orders_3m_rolling"] = monthly["total_orders"].rolling(3, min_periods=1).mean().round(1)
    monthly["orders_6m_rolling"] = monthly["total_orders"].rolling(6, min_periods=1).mean().round(1)

    # YoY comparison (where both year exist)
    monthly["year"] = monthly["year_month_str"].str[:4].astype(int)
    monthly["month"] = monthly["year_month_str"].str[5:7].astype(int)
    monthly_pivot = monthly.set_index(["year", "month"])
    yoy_list = []
    for _, row in monthly.iterrows():
        yr, mo = int(row["year"]), int(row["month"])
        prior_yr = yr - 1
        if (prior_yr, mo) in monthly_pivot.index:
            prior_orders = monthly_pivot.loc[(prior_yr, mo), "total_orders"]
            yoy = (row["total_orders"] - prior_orders) / prior_orders * 100
        else:
            yoy = np.nan
        yoy_list.append(round(yoy, 2) if not np.isnan(yoy) else None)
    monthly["orders_yoy_pct"] = yoy_list

    return monthly


def category_performance(df_cats: pd.DataFrame, fact: pd.DataFrame) -> pd.DataFrame:
    """Category-level performance analysis with Pareto and growth."""
    df_cats = df_cats.copy()
    df_cats["revenue_completed"] = df_cats["total_pembayaran"].where(df_cats["is_completed"] == 1, 0)
    cat = (
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
        .reset_index(drop=True)
    )
    cat["cancellation_rate"] = (
        cat["cancelled_orders"] / cat["total_orders"] * 100
    ).round(2)
    cat["order_share_pct"] = (
        cat["total_orders"] / cat["total_orders"].sum() * 100
    ).round(2)
    cat["revenue_share_pct"] = (
        cat["total_revenue"] / cat["total_revenue"].sum() * 100
    ).round(2)
    cat["cumulative_order_share"] = cat["order_share_pct"].cumsum().round(2)
    cat["pareto_flag"] = (cat["cumulative_order_share"] <= 80).astype(int)  # top 80%
    cat["avg_order_value"] = (
        cat["total_revenue"] / cat["completed_orders"].replace(0, np.nan)
    ).round(0)

    # Half-year growth: compare first 12 months vs last 12 months
    df_cats["half"] = df_cats["year_month_str"].apply(
        lambda x: "first_half" if x <= "2024-11" else "second_half"
    )
    cat_halves = (
        df_cats.groupby(["category", "half"])["order_id"]
        .count()
        .unstack(fill_value=0)
        .reset_index()
    )
    if "first_half" in cat_halves.columns and "second_half" in cat_halves.columns:
        cat_halves["growth_pct"] = (
            (cat_halves["second_half"] - cat_halves["first_half"]) /
            cat_halves["first_half"].replace(0, np.nan) * 100
        ).round(2)
        cat = cat.merge(cat_halves[["category", "growth_pct"]], on="category", how="left")

    return cat


def payment_analysis(fact: pd.DataFrame) -> pd.DataFrame:
    """Payment method performance and cancellation by payment type."""
    fact = fact.copy()
    fact["revenue_completed"] = fact["total_pembayaran"].where(fact["is_completed"] == 1, 0)
    pay = (
        fact.groupby("metode_pembayaran")
        .agg(
            total_orders=("order_id", "count"),
            completed_orders=("is_completed", "sum"),
            cancelled_orders=("is_cancelled", "sum"),
            total_revenue=("revenue_completed", "sum"),
        )
        .reset_index()
        .sort_values("total_orders", ascending=False)
    )
    pay["avg_order_value"] = (
        pay["total_revenue"] / pay["completed_orders"].replace(0, np.nan)
    ).round(0)
    pay["cancellation_rate"] = (
        pay["cancelled_orders"] / pay["total_orders"] * 100
    ).round(2)
    pay["order_share_pct"] = (
        pay["total_orders"] / pay["total_orders"].sum() * 100
    ).round(2)
    return pay


def regional_performance(fact: pd.DataFrame) -> pd.DataFrame:
    """Province-level performance with growth segmentation."""
    fact = fact.copy()
    fact["revenue_completed"] = fact["total_pembayaran"].where(fact["is_completed"] == 1, 0)
    geo = (
        fact.groupby("province_clean")
        .agg(
            total_orders=("order_id", "count"),
            completed_orders=("is_completed", "sum"),
            cancelled_orders=("is_cancelled", "sum"),
            total_revenue=("revenue_completed", "sum"),
            avg_shipping=("perkiraan_ongkir", "mean"),
            region_group=("region_group", "first"),
        )
        .reset_index()
        .sort_values("total_orders", ascending=False)
    )
    geo["cancellation_rate"] = (
        geo["cancelled_orders"] / geo["total_orders"] * 100
    ).round(2)
    geo["order_share_pct"] = (
        geo["total_orders"] / geo["total_orders"].sum() * 100
    ).round(2)

    # Growth: first vs second half of dataset
    fact["half"] = fact["year_month_str"].apply(
        lambda x: "first_half" if str(x) <= "2024-11" else "second_half"
    )
    geo_halves = (
        fact.groupby(["province_clean", "half"])["order_id"]
        .count()
        .unstack(fill_value=0)
        .reset_index()
    )
    if "first_half" in geo_halves.columns and "second_half" in geo_halves.columns:
        geo_halves["growth_pct"] = (
            (geo_halves["second_half"] - geo_halves["first_half"]) /
            geo_halves["first_half"].replace(0, np.nan) * 100
        ).round(2)
        geo = geo.merge(
            geo_halves[["province_clean", "growth_pct"]], on="province_clean", how="left"
        )

    return geo


def concentration_analysis(fact: pd.DataFrame) -> dict:
    """Herfindahl-Hirschman Index for concentration by province and category."""
    # Province concentration
    prov_shares = (fact.groupby("province_clean").size() / len(fact)).values
    hhi_province = float(np.sum(prov_shares ** 2))

    # Top-5 concentration
    top5_pct = float(
        fact.groupby("province_clean").size().nlargest(5).sum() / len(fact) * 100
    )

    return {
        "hhi_province": round(hhi_province, 4),
        "top5_province_concentration_pct": round(top5_pct, 2),
        "interpretation": (
            "High concentration (>0.25 HHI)" if hhi_province > 0.25 else
            "Moderate concentration (0.15-0.25)" if hhi_province > 0.15 else
            "Low concentration (<0.15)"
        ),
    }


def run_sales_analytics(fact: pd.DataFrame, df_cats: pd.DataFrame) -> dict:
    """Run full sales analytics suite."""
    logger.info("Running sales analytics...")
    results = {
        "monthly_trend": monthly_sales_trend(fact),
        "category_performance": category_performance(df_cats, fact),
        "payment_analysis": payment_analysis(fact),
        "regional_performance": regional_performance(fact),
        "concentration": concentration_analysis(fact),
    }
    logger.info("Sales analytics complete.")
    return results


def save_sales_analytics(results: dict, output_dir: str = REPORTS_PATH) -> None:
    """Save sales analytics results."""
    os.makedirs(output_dir, exist_ok=True)
    for name, data in results.items():
        if isinstance(data, pd.DataFrame):
            path = os.path.join(output_dir, f"sales_{name}.parquet")
            data.to_parquet(path, index=False)
            logger.info(f"  Saved sales_{name}: {len(data)} rows")
        elif isinstance(data, dict):
            path = os.path.join(output_dir, f"sales_{name}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
    fact = pd.read_parquet(os.path.join(MARTS_PATH, "fact_orders.parquet"))
    df_cats = pd.read_parquet(os.path.join(PROCESSED_PATH, "orders_categories.parquet"))
    results = run_sales_analytics(fact, df_cats)
    save_sales_analytics(results)

    print("\nMonthly Trend (last 6 months):")
    print(results["monthly_trend"].tail(6)[
        ["year_month_str", "total_orders", "cancellation_rate", "orders_mom_pct"]
    ].to_string(index=False))

    print("\nTop 10 Categories:")
    print(results["category_performance"].head(10)[
        ["category", "total_orders", "order_share_pct", "cancellation_rate"]
    ].to_string(index=False))

    print("\nPayment Analysis:")
    print(results["payment_analysis"][
        ["metode_pembayaran", "total_orders", "order_share_pct", "cancellation_rate"]
    ].to_string(index=False))

    print(f"\nConcentration: {results['concentration']}")
