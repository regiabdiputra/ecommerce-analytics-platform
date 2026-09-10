"""
Transformation module — feature engineering on staged data.
Derives analytical columns from existing fields.
Output: data/processed/orders_enriched.parquet
         data/processed/orders_categories.parquet
"""
import pandas as pd
import numpy as np
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
)
STAGING_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "staging")
)


def _safe_divide(numerator: pd.Series, denominator: pd.Series,
                 fill_value: float = 0.0) -> pd.Series:
    """Safe division avoiding divide-by-zero."""
    return np.where(denominator > 0, numerator / denominator, fill_value)


def build_features(stg: pd.DataFrame) -> pd.DataFrame:
    """
    Derive all analytical features from staged data.
    Every column has an explicit formula documented below.
    """
    logger.info("Building analytical features...")
    df = stg.copy()

    # ── Time features ─────────────────────────────────────────────────────────
    logger.info("  Deriving time features...")

    # order_year: calendar year from datetime, fallback to year_month_str
    df["order_year"] = df["order_datetime"].dt.year
    mask_no_dt = df["order_year"].isna() & df["year_month_str"].notna()
    df.loc[mask_no_dt, "order_year"] = (
        df.loc[mask_no_dt, "year_month_str"].str[:4].astype(float)
    )

    # order_month: 1-12
    df["order_month"] = df["order_datetime"].dt.month
    mask_no_dt = df["order_month"].isna() & df["year_month_str"].notna()
    df.loc[mask_no_dt, "order_month"] = (
        df.loc[mask_no_dt, "year_month_str"].str[5:7].astype(float)
    )

    # order_month_name: January … December
    month_names = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
                   7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}
    df["order_month_name"] = df["order_month"].map(month_names)

    # order_quarter: 1-4
    df["order_quarter"] = df["order_datetime"].dt.quarter
    mask_no_dt = df["order_quarter"].isna() & df["order_month"].notna()
    df.loc[mask_no_dt, "order_quarter"] = np.ceil(df.loc[mask_no_dt, "order_month"] / 3).astype("Int64")

    # year_quarter: e.g. "2024-Q3"
    df["year_quarter"] = (
        df["order_year"].astype("Int64").astype(str) + "-Q" +
        df["order_quarter"].astype("Int64").astype(str)
    )

    # order_week: ISO week number
    df["order_week"] = df["order_datetime"].dt.isocalendar().week.astype("Int64")

    # order_day: day of month
    df["order_day"] = df["order_datetime"].dt.day

    # order_dayofweek: 0=Monday … 6=Sunday
    df["order_dayofweek"] = df["order_datetime"].dt.dayofweek

    # order_hour: 0-23
    df["order_hour"] = df["order_datetime"].dt.hour

    # order_date: date only (no time)
    df["order_date"] = df["order_datetime"].dt.date

    # ── Binary flags ──────────────────────────────────────────────────────────
    logger.info("  Deriving binary flags...")

    # is_cancelled: 1 if status_normalized == 'cancelled'
    df["is_cancelled"] = (df["status_normalized"] == "cancelled").astype(int)

    # is_completed: 1 if status is completed or completed_review
    df["is_completed"] = df["status_normalized"].isin(
        ["completed", "completed_review"]
    ).astype(int)

    # is_terminal: 1 if order is in final state (completed or cancelled)
    df["is_terminal"] = df["status_normalized"].isin(
        ["completed", "completed_review", "cancelled"]
    ).astype(int)

    # is_cod: 1 if payment is COD
    df["is_cod"] = df["metode_pembayaran"].str.contains(
        r"(?i)cod|bayar di tempat", na=False
    ).astype(int)

    # has_discount: 1 if total_diskon > 0
    df["has_discount"] = (df["total_diskon"] > 0).astype(int)

    # is_multi_category: 1 if num_product_categories > 1
    df["is_multi_category"] = (df["num_product_categories"] > 1).astype(int)

    # is_returned: 1 if total_returned_qty > 0
    df["is_returned"] = (df["total_returned_qty"] > 0).astype(int)

    # is_free_shipping: 1 if buyer paid 0 shipping
    df["is_free_shipping"] = (df["ongkir_dibayar_pembeli"] == 0).astype(int)

    # is_subsidized: 1 if platform provided shipping subsidy > 0
    df["is_subsidized"] = (df["estimasi_potongan_ongkir"] > 0).astype(int)

    # is_bulk_order: 1 if total_qty >= 10 (p99 threshold)
    df["is_bulk_order"] = (df["total_qty"] >= 10).astype(int)

    # ── Derived ratios ────────────────────────────────────────────────────────
    logger.info("  Deriving ratios and monetary metrics...")

    # weight_kg: total_weight_gr / 1000
    df["weight_kg"] = df["total_weight_gr"] / 1000

    # shipping_subsidy_ratio: Estimasi Potongan / Perkiraan Ongkos Kirim
    # Proportion of shipping cost covered by platform
    df["shipping_subsidy_ratio"] = _safe_divide(
        df["estimasi_potongan_ongkir"].astype(float),
        df["perkiraan_ongkir"].astype(float),
        fill_value=0.0,
    )
    df["shipping_subsidy_ratio"] = df["shipping_subsidy_ratio"].clip(0, 1)

    # shipping_cost_buyer_ratio: buyer paid / full shipping cost
    df["shipping_cost_buyer_ratio"] = _safe_divide(
        df["ongkir_dibayar_pembeli"].astype(float),
        df["perkiraan_ongkir"].astype(float),
        fill_value=0.0,
    )
    df["shipping_cost_buyer_ratio"] = df["shipping_cost_buyer_ratio"].clip(0, 1)

    # shipping_cost_per_kg: Perkiraan Ongkos / weight_kg (only for non-zero weight)
    df["shipping_cost_per_kg"] = _safe_divide(
        df["perkiraan_ongkir"].astype(float),
        df["weight_kg"],
        fill_value=0.0,
    )

    # discount_ratio: total_diskon / total_pembayaran
    df["discount_ratio"] = _safe_divide(
        df["total_diskon"].astype(float),
        (df["total_pembayaran"] + df["total_diskon"]).astype(float),
        fill_value=0.0,
    )
    df["discount_ratio"] = df["discount_ratio"].clip(0, 1)

    # avg_item_payment: total_pembayaran / total_qty (proxy for avg item price)
    df["avg_item_payment"] = _safe_divide(
        df["total_pembayaran"].astype(float),
        df["total_qty"].astype(float),
        fill_value=0.0,
    )

    # ── Geography features ────────────────────────────────────────────────────
    # geography_key: province|city composite key
    df["geography_key"] = df["province_clean"] + "|" + df["city_clean"]

    # ── Peak season flag ──────────────────────────────────────────────────────
    # Jul-Aug observed as peak from data inspection
    df["is_peak_season"] = df["order_month"].isin([7, 8]).astype(int)

    # ── Payment type grouping ─────────────────────────────────────────────────
    def _payment_type(method):
        if pd.isna(method):
            return "unknown"
        m = str(method).lower()
        if "cod" in m or "bayar di tempat" in m:
            return "COD"
        if "spaylater" in m or "kredit" in m or "debit" in m or "cicil" in m:
            return "BNPL/Credit"
        if "shopee" in m or "saldo" in m or "seabank" in m or "online" in m:
            return "Digital Wallet"
        return "Other Digital"

    df["payment_type"] = df["metode_pembayaran"].apply(_payment_type)

    # ── Order value tier ──────────────────────────────────────────────────────
    def _value_tier(payment):
        if payment == 0:
            return "zero"
        elif payment < 20000:
            return "low"         # < 20K IDR
        elif payment < 50000:
            return "medium"      # 20K–50K IDR
        elif payment < 150000:
            return "high"        # 50K–150K IDR
        else:
            return "very_high"   # > 150K IDR

    df["order_value_tier"] = df["total_pembayaran"].apply(_value_tier)

    logger.info(f"Feature engineering complete: {df.shape[1]} columns total")
    return df


def build_category_exploded(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create category-exploded view: one row per (order_id, category).
    Used for category-level aggregations.
    """
    logger.info("Building category-exploded view...")
    exploded = df[["order_id", "product_categories", "total_qty",
                   "total_pembayaran", "perkiraan_ongkir",
                   "is_cancelled", "is_completed", "year_month_str",
                   "order_year", "order_month", "province_clean",
                   "region_group", "java_bali_flag",
                   "status_normalized"]].copy()

    exploded["category"] = exploded["product_categories"].str.split(", ")
    exploded = exploded.explode("category")
    exploded["category"] = exploded["category"].str.strip()
    exploded = exploded.dropna(subset=["category"])
    exploded = exploded[exploded["category"] != ""]

    logger.info(f"Category-exploded: {len(exploded):,} rows (from {len(df):,} orders)")
    return exploded


def save_processed(df: pd.DataFrame, df_cat: pd.DataFrame,
                   output_dir: str = PROCESSED_PATH) -> tuple:
    """Save enriched and category-exploded DataFrames to parquet."""
    os.makedirs(output_dir, exist_ok=True)

    path_enriched = os.path.join(output_dir, "orders_enriched.parquet")
    path_cats = os.path.join(output_dir, "orders_categories.parquet")

    df.to_parquet(path_enriched, index=False, engine="pyarrow")
    df_cat.to_parquet(path_cats, index=False, engine="pyarrow")

    logger.info(f"Saved enriched: {path_enriched} ({os.path.getsize(path_enriched)/1024:.1f} KB)")
    logger.info(f"Saved categories: {path_cats} ({os.path.getsize(path_cats)/1024:.1f} KB)")
    return path_enriched, path_cats


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))

    stg_path = os.path.join(STAGING_PATH, "stg_orders.parquet")
    if not os.path.exists(stg_path):
        logger.error(f"Staging file not found: {stg_path}. Run staging.py first.")
        sys.exit(1)

    stg = pd.read_parquet(stg_path)
    df_enriched = build_features(stg)
    df_cats = build_category_exploded(df_enriched)
    save_processed(df_enriched, df_cats)

    logger.info("Transformation complete.")
    logger.info(f"  Columns: {df_enriched.shape[1]}")
    logger.info(f"  Cancellation rate: {df_enriched['is_cancelled'].mean()*100:.1f}%")
    logger.info(f"  Completed rate: {df_enriched['is_completed'].mean()*100:.1f}%")
    logger.info(f"  COD rate: {df_enriched['is_cod'].mean()*100:.1f}%")
    logger.info(f"  Free shipping rate: {df_enriched['is_free_shipping'].mean()*100:.1f}%")
