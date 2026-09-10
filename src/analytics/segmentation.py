"""
Segmentation module — strategic quadrant analysis for regions and categories.
Converts descriptive analytics into decision support segments.
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


def region_segmentation(fact: pd.DataFrame) -> pd.DataFrame:
    """
    Segment provinces by Volume × Growth quadrant.
    Quadrants:
      High Volume / High Growth  → Star Markets
      High Volume / Low Growth   → Cash Cow Markets
      Low Volume / High Growth   → Emerging Markets
      Low Volume / Low Growth    → Lagging Markets
    """
    # Volume = total orders
    prov_total = (
        fact.groupby("province_clean")
        .agg(total_orders=("order_id", "count"))
        .reset_index()
    )

    # Growth = % change from first half (Dec23-Nov24) to second half (Dec24-Nov25)
    fact_copy = fact.copy()
    fact_copy["period"] = fact_copy["year_month_str"].apply(
        lambda x: "first" if str(x) <= "2024-11" else "second"
    )
    prov_periods = (
        fact_copy.groupby(["province_clean", "period"])["order_id"]
        .count()
        .unstack(fill_value=0)
        .reset_index()
    )
    if "first" in prov_periods.columns and "second" in prov_periods.columns:
        prov_periods["growth_pct"] = (
            (prov_periods["second"] - prov_periods["first"]) /
            prov_periods["first"].replace(0, np.nan) * 100
        ).round(2)
    else:
        prov_periods["growth_pct"] = 0.0

    seg = prov_total.merge(
        prov_periods[["province_clean", "growth_pct"]], on="province_clean", how="left"
    )
    seg["growth_pct"] = seg["growth_pct"].fillna(0)

    # Thresholds: median
    vol_threshold = seg["total_orders"].median()
    growth_threshold = seg["growth_pct"].median()

    def _quadrant(row):
        hi_vol = row["total_orders"] >= vol_threshold
        hi_growth = row["growth_pct"] >= growth_threshold
        if hi_vol and hi_growth:
            return "Star Markets"
        if hi_vol and not hi_growth:
            return "Cash Cow Markets"
        if not hi_vol and hi_growth:
            return "Emerging Markets"
        return "Lagging Markets"

    seg["segment"] = seg.apply(_quadrant, axis=1)
    seg["volume_threshold"] = round(vol_threshold, 0)
    seg["growth_threshold"] = round(growth_threshold, 2)

    # Add cancellation rate
    cancel_by_prov = (
        fact.groupby("province_clean")
        .agg(
            cancel_rate=("is_cancelled", "mean"),
            region_group=("region_group", "first"),
        )
        .reset_index()
    )
    cancel_by_prov["cancel_rate"] = (cancel_by_prov["cancel_rate"] * 100).round(2)
    seg = seg.merge(cancel_by_prov, on="province_clean", how="left")
    seg = seg.sort_values("total_orders", ascending=False).reset_index(drop=True)

    return seg


def category_segmentation(df_cats: pd.DataFrame) -> pd.DataFrame:
    """
    Segment categories by Volume × Growth quadrant.
    Same logic as region segmentation.
    """
    cat_total = (
        df_cats.groupby("category")
        .agg(total_orders=("order_id", "count"))
        .reset_index()
    )

    df_cats_copy = df_cats.copy()
    df_cats_copy["period"] = df_cats_copy["year_month_str"].apply(
        lambda x: "first" if str(x) <= "2024-11" else "second"
    )
    cat_periods = (
        df_cats_copy.groupby(["category", "period"])["order_id"]
        .count()
        .unstack(fill_value=0)
        .reset_index()
    )
    if "first" in cat_periods.columns and "second" in cat_periods.columns:
        cat_periods["growth_pct"] = (
            (cat_periods["second"] - cat_periods["first"]) /
            cat_periods["first"].replace(0, np.nan) * 100
        ).round(2)
    else:
        cat_periods["growth_pct"] = 0.0

    seg = cat_total.merge(
        cat_periods[["category", "growth_pct"]], on="category", how="left"
    )
    seg["growth_pct"] = seg["growth_pct"].fillna(0)

    vol_threshold = seg["total_orders"].median()
    growth_threshold = seg["growth_pct"].median()

    def _quadrant(row):
        hi_vol = row["total_orders"] >= vol_threshold
        hi_growth = row["growth_pct"] >= growth_threshold
        if hi_vol and hi_growth:
            return "Star Categories"
        if hi_vol and not hi_growth:
            return "Core Categories"
        if not hi_vol and hi_growth:
            return "Emerging Categories"
        return "Niche Categories"

    seg["segment"] = seg.apply(_quadrant, axis=1)
    seg["volume_threshold"] = round(vol_threshold, 0)
    seg["growth_threshold"] = round(growth_threshold, 2)

    # Add cancel rate
    cancel_by_cat = (
        df_cats.groupby("category")
        .agg(cancel_rate=("is_cancelled", "mean"))
        .reset_index()
    )
    cancel_by_cat["cancel_rate"] = (cancel_by_cat["cancel_rate"] * 100).round(2)
    seg = seg.merge(cancel_by_cat, on="category", how="left")
    seg = seg.sort_values("total_orders", ascending=False).reset_index(drop=True)

    return seg


def run_segmentation(fact: pd.DataFrame, df_cats: pd.DataFrame) -> dict:
    """Run full segmentation suite."""
    logger.info("Running segmentation analysis...")
    results = {
        "region_segments": region_segmentation(fact),
        "category_segments": category_segmentation(df_cats),
    }
    logger.info("Segmentation complete.")
    return results


def save_segmentation(results: dict, output_dir: str = REPORTS_PATH) -> None:
    """Save segmentation results."""
    os.makedirs(output_dir, exist_ok=True)
    for name, data in results.items():
        if isinstance(data, pd.DataFrame):
            path = os.path.join(output_dir, f"seg_{name}.parquet")
            data.to_parquet(path, index=False)
            logger.info(f"  Saved seg_{name}: {len(data)} rows")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
    fact = pd.read_parquet(os.path.join(MARTS_PATH, "fact_orders.parquet"))
    df_cats = pd.read_parquet(os.path.join(PROCESSED_PATH, "orders_categories.parquet"))

    results = run_segmentation(fact, df_cats)
    save_segmentation(results)

    print("\nRegion Segments:")
    print(results["region_segments"][
        ["province_clean", "total_orders", "growth_pct", "cancel_rate", "segment"]
    ].head(15).to_string(index=False))

    print("\nCategory Segments:")
    print(results["category_segments"][
        ["category", "total_orders", "growth_pct", "cancel_rate", "segment"]
    ].head(15).to_string(index=False))
