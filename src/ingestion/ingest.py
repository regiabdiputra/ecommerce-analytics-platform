"""
Ingestion module — loads raw CSV into memory and saves a clean copy.
Raw file is NEVER modified. This module only reads and validates file access.
"""
import pandas as pd
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RAW_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "all_months_clean.csv")
RAW_PATH = os.path.normpath(RAW_PATH)

EXPECTED_COLUMNS = [
    "order_id", "total_qty", "total_weight_gr", "total_returned_qty",
    "Total Diskon", "product_categories", "num_product_categories",
    "Status Pesanan", "Alasan Pembatalan", "Opsi Pengiriman",
    "Metode Pembayaran", "Kota/Kabupaten", "Provinsi",
    "Ongkos Kirim Dibayar oleh Pembeli", "Estimasi Potongan Biaya Pengiriman",
    "Total Pembayaran", "Perkiraan Ongkos Kirim",
    "Waktu Pesanan Dibuat", "source_file"
]

DTYPE_MAP = {
    "order_id": str,
    "total_qty": "int64",
    "total_weight_gr": "int64",
    "total_returned_qty": "int64",
    "Total Diskon": "int64",
    "product_categories": str,
    "num_product_categories": "int64",
    "Status Pesanan": str,
    "Alasan Pembatalan": str,
    "Opsi Pengiriman": str,
    "Metode Pembayaran": str,
    "Kota/Kabupaten": str,
    "Provinsi": str,
    "Ongkos Kirim Dibayar oleh Pembeli": "int64",
    "Estimasi Potongan Biaya Pengiriman": "int64",
    "Total Pembayaran": "int64",
    "Perkiraan Ongkos Kirim": "int64",
    "Waktu Pesanan Dibuat": str,
    "source_file": str,
}


def load_raw(path: str = RAW_PATH) -> pd.DataFrame:
    """
    Load the raw CSV file without modifying anything.
    Returns a DataFrame with correct dtypes.
    Raises FileNotFoundError or ValueError on critical failures.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Raw data file not found: {path}")

    logger.info(f"Loading raw data from: {path}")
    df = pd.read_csv(
        path,
        sep=";",
        encoding="utf-8-sig",
        low_memory=False,
        dtype={
            k: v for k, v in DTYPE_MAP.items()
            if v not in ("int64",)  # let pandas infer numerics first
        },
    )

    logger.info(f"Loaded {len(df):,} rows x {df.shape[1]} columns")

    # Validate column presence
    missing_cols = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing expected columns: {missing_cols}")

    extra_cols = [c for c in df.columns if c not in EXPECTED_COLUMNS]
    if extra_cols:
        logger.warning(f"Unexpected extra columns found: {extra_cols}")

    return df


def get_raw_stats(df: pd.DataFrame) -> dict:
    """Return basic stats dict for logging/reporting."""
    return {
        "rows": len(df),
        "columns": df.shape[1],
        "order_id_unique": int(df["order_id"].nunique()),
        "date_min": str(df["Waktu Pesanan Dibuat"].dropna().min()),
        "date_max": str(df["Waktu Pesanan Dibuat"].dropna().max()),
        "missing_timestamp": int(df["Waktu Pesanan Dibuat"].isna().sum()),
        "source_files": int(df["source_file"].nunique()),
    }


if __name__ == "__main__":
    df = load_raw()
    stats = get_raw_stats(df)
    for k, v in stats.items():
        logger.info(f"  {k}: {v}")
    logger.info("Ingestion complete — raw data loaded successfully.")
