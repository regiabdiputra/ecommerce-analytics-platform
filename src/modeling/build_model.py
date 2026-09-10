"""
Dimensional model builder — creates star schema from enriched data.
Output: data/marts/fact_orders.parquet, data/marts/dim_*.parquet
"""
import pandas as pd
import numpy as np
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MARTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "marts")
)
PROCESSED_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
)


def build_dim_date(df: pd.DataFrame) -> pd.DataFrame:
    """Build date dimension from all year_month_str values in the dataset."""
    logger.info("  Building dim_date...")
    months = df["year_month_str"].dropna().unique()
    records = []
    month_names = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
                   7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}
    for ym in sorted(months):
        try:
            year = int(ym[:4])
            month = int(ym[5:7])
            quarter = (month - 1) // 3 + 1
            records.append({
                "year_month_key": ym,
                "year": year,
                "month": month,
                "month_name": month_names.get(month, ""),
                "quarter": quarter,
                "year_quarter": f"{year}-Q{quarter}",
                "is_peak_season": 1 if month in [7, 8] else 0,
                "is_year_end": 1 if month == 12 else 0,
                "is_ramadan_approx": 1 if (year == 2024 and month in [3, 4]) or
                                          (year == 2025 and month in [2, 3]) else 0,
            })
        except Exception:
            continue
    dim = pd.DataFrame(records).drop_duplicates(subset=["year_month_key"])
    logger.info(f"    dim_date: {len(dim)} records")
    return dim


def build_dim_geography(df: pd.DataFrame) -> pd.DataFrame:
    """Build geography dimension from province and city combinations."""
    logger.info("  Building dim_geography...")
    geo = (
        df[["geography_key", "province_clean", "city_clean",
            "city_type", "region_group", "java_bali_flag"]]
        .drop_duplicates(subset=["geography_key"])
        .reset_index(drop=True)
    )
    geo = geo.rename(columns={
        "province_clean": "province",
        "city_clean": "city",
    })
    logger.info(f"    dim_geography: {len(geo)} records ({geo['province'].nunique()} provinces)")
    return geo


def build_dim_product_category(df_cats: pd.DataFrame) -> pd.DataFrame:
    """Build product category dimension from exploded category data."""
    logger.info("  Building dim_product_category...")
    categories = df_cats["category"].dropna().unique()

    # Assign category groups based on actual categories found
    kitchen_cats = {
        "Mangkok Sambal / Saus", "Baskom / Mangkok Besar", "Lunch Box / Rantang",
        "Tempat Nasi", "Teko / Pitcher", "Sendok / Garpu / Sumpit",
        "Nampan / Tray", "Wadah Makanan", "Panci / Wajan",
    }
    storage_cats = {
        "Celengan", "Keranjang", "Rak / Rak Serbaguna", "Toples / Sealware",
        "Laci / Drawer", "Kotak Penyimpanan", "Tempat Sepatu",
        "Tempat Pakaian", "Hanger",
    }
    bathroom_cats = {
        "Peralatan Kamar Mandi", "Aksesoris Mandi", "Ember / Baskom Mandi",
        "Gayung", "Tempat Sabun", "Sikat",
    }
    door_acc_cats = {
        "Aksesoris Pintu", "Seal / Baut / Roof", "Kunci / Gembok",
    }

    def _category_group(cat):
        if cat in kitchen_cats:
            return "Kitchen & Dining"
        if cat in storage_cats:
            return "Storage & Organization"
        if cat in bathroom_cats:
            return "Bathroom"
        if cat in door_acc_cats:
            return "Door & Hardware"
        return "Other Household"

    records = []
    for cat in sorted(categories):
        records.append({
            "category_key": cat.lower().replace(" ", "_").replace("/", "_"),
            "category_name": cat,
            "category_group": _category_group(cat),
        })
    dim = pd.DataFrame(records).drop_duplicates(subset=["category_key"])
    logger.info(f"    dim_product_category: {len(dim)} categories")
    return dim


def build_dim_payment(df: pd.DataFrame) -> pd.DataFrame:
    """Build payment dimension."""
    logger.info("  Building dim_payment...")
    methods = df[["metode_pembayaran", "payment_type", "is_cod"]].drop_duplicates(
        subset=["metode_pembayaran"]
    ).reset_index(drop=True)
    methods["payment_key"] = (
        methods["metode_pembayaran"]
        .str.lower()
        .str.replace(r"[^a-z0-9]", "_", regex=True)
        .str.strip("_")
    )
    methods = methods.rename(columns={"metode_pembayaran": "payment_method"})
    logger.info(f"    dim_payment: {len(methods)} payment methods")
    return methods


def build_dim_shipping(df: pd.DataFrame) -> pd.DataFrame:
    """Build shipping dimension from parsed tier and courier."""
    logger.info("  Building dim_shipping...")
    shipping = (
        df[["opsi_pengiriman_raw", "shipping_tier", "shipping_courier"]]
        .drop_duplicates(subset=["opsi_pengiriman_raw"])
        .reset_index(drop=True)
    )
    shipping["shipping_key"] = (
        shipping["shipping_tier"] + "|" + shipping["shipping_courier"]
    )
    shipping = shipping.rename(columns={"opsi_pengiriman_raw": "raw_option"})
    logger.info(f"    dim_shipping: {len(shipping)} shipping options → "
                f"{shipping['shipping_key'].nunique()} unique tier|courier combos")
    return shipping


def build_dim_status(df: pd.DataFrame) -> pd.DataFrame:
    """Build status dimension."""
    logger.info("  Building dim_status...")
    status = (
        df[["status_normalized", "status_raw"]]
        .drop_duplicates(subset=["status_normalized"])
        .reset_index(drop=True)
    )
    status["status_key"] = status["status_normalized"]
    terminal_statuses = {"completed", "completed_review", "cancelled"}
    status["is_terminal"] = status["status_normalized"].isin(terminal_statuses).astype(int)
    status["is_success"] = status["status_normalized"].isin(
        {"completed", "completed_review"}
    ).astype(int)
    logger.info(f"    dim_status: {len(status)} status values")
    return status


def build_fact_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Build central fact table with FK references and measures."""
    logger.info("  Building fact_orders...")

    fact_cols = [
        # Keys
        "order_id", "year_month_str", "order_date", "geography_key",
        "metode_pembayaran", "opsi_pengiriman_raw", "status_normalized",
        # Measures
        "total_qty", "total_weight_gr", "total_returned_qty", "total_diskon",
        "ongkir_dibayar_pembeli", "estimasi_potongan_ongkir",
        "total_pembayaran", "perkiraan_ongkir", "num_product_categories",
        # Derived measures
        "weight_kg", "shipping_subsidy_ratio", "shipping_cost_buyer_ratio",
        "shipping_cost_per_kg", "discount_ratio", "avg_item_payment",
        # Cancellation detail
        "cancellation_reason_clean", "cancellation_initiator",
        # Flags
        "is_cancelled", "is_completed", "is_terminal", "is_cod",
        "has_discount", "is_multi_category", "is_returned",
        "is_free_shipping", "is_subsidized", "is_bulk_order",
        "java_bali_flag", "is_peak_season",
        # Dimension context
        "order_year", "order_month", "order_quarter", "order_hour",
        "order_dayofweek", "payment_type", "order_value_tier",
        "shipping_tier", "shipping_courier", "region_group",
        "province_clean", "city_clean", "city_type",
        # Category (primary — single value from product_categories)
        "product_categories",
    ]
    # Only include columns that exist in df
    available = [c for c in fact_cols if c in df.columns]
    fact = df[available].copy()

    # Add FK keys matching dimension tables
    fact["payment_key"] = (
        fact["metode_pembayaran"]
        .str.lower()
        .str.replace(r"[^a-z0-9]", "_", regex=True)
        .str.strip("_")
    )
    fact["shipping_key"] = fact["shipping_tier"] + "|" + fact["shipping_courier"]
    fact["status_key"] = fact["status_normalized"]
    fact["date_key"] = fact["year_month_str"]

    logger.info(f"    fact_orders: {len(fact):,} rows, {fact.shape[1]} columns")
    return fact


def build_dimensional_model(df: pd.DataFrame, df_cats: pd.DataFrame) -> dict:
    """Build all dimensional model tables."""
    logger.info("Building dimensional model...")
    model = {
        "dim_date": build_dim_date(df),
        "dim_geography": build_dim_geography(df),
        "dim_product_category": build_dim_product_category(df_cats),
        "dim_payment": build_dim_payment(df),
        "dim_shipping": build_dim_shipping(df),
        "dim_status": build_dim_status(df),
        "fact_orders": build_fact_orders(df),
    }
    return model


def save_model(model: dict, output_dir: str = MARTS_PATH) -> None:
    """Save all dimensional model tables to parquet."""
    os.makedirs(output_dir, exist_ok=True)
    for name, table in model.items():
        path = os.path.join(output_dir, f"{name}.parquet")
        table.to_parquet(path, index=False, engine="pyarrow")
        size_kb = os.path.getsize(path) / 1024
        logger.info(f"  Saved {name}: {len(table):,} rows ({size_kb:.1f} KB)")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))

    enriched_path = os.path.join(PROCESSED_PATH, "orders_enriched.parquet")
    cats_path = os.path.join(PROCESSED_PATH, "orders_categories.parquet")

    if not os.path.exists(enriched_path):
        logger.error(f"Enriched data not found: {enriched_path}. Run transform.py first.")
        sys.exit(1)

    df = pd.read_parquet(enriched_path)
    df_cats = pd.read_parquet(cats_path)

    model = build_dimensional_model(df, df_cats)
    save_model(model)

    logger.info("\nDimensional model summary:")
    for name, table in model.items():
        logger.info(f"  {name:<30} {len(table):>6,} rows x {table.shape[1]:>2} cols")
    logger.info("Dimensional model build complete.")
