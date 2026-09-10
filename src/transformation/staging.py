"""
Staging module — cleans and normalizes raw data.
Output: data/staging/stg_orders.parquet
No new analytical columns — only corrections and type fixes.
"""
import pandas as pd
import numpy as np
import os
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

STAGING_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "staging")
)

# ── Status normalization map ───────────────────────────────────────────────────
STATUS_MAP = {
    "Selesai": "completed",
    "Batal": "cancelled",
    "Sedang Dikirim": "in_transit",
    "Telah Dikirim": "shipped",
}

# ── Cancellation initiator patterns ───────────────────────────────────────────
CANCEL_INITIATOR_PATTERNS = [
    (r"(?i)dibatalkan oleh pembeli|buyer|pembeli", "buyer"),
    (r"(?i)dibatalkan oleh penjual|seller|penjual", "seller"),
    (r"(?i)sistem|system|otomatis|expired|belum dibayar|gagal kirim|gagal pengiriman", "system"),
]

CANCEL_REASON_MAP = {
    r"(?i)ubah pesanan|change.*order|modify": "wants_to_modify_order",
    r"(?i)berubah pikiran|lainnya|changed.*mind|other": "changed_mind",
    r"(?i)belum dibayar|not.*paid|unpaid|payment.*expired": "not_paid",
    r"(?i)ubah.*alamat|change.*address|wrong.*address|salah.*alamat": "wrong_address",
    r"(?i)gagal.*kirim|delivery.*fail|pengiriman.*gagal|failed.*delivery": "delivery_failed",
    r"(?i)terlambat.*kirim|late.*ship|penjual.*gagal|seller.*fail": "seller_late_to_ship",
    r"(?i)barang.*rusak|damaged|kerusakan": "damaged_goods",
    r"(?i)stok.*habis|out.*of.*stock|tidak.*tersedia": "out_of_stock",
    r"(?i)harga|price|mahal": "price_issue",
    r"(?i)duplikat|duplicate": "duplicate_order",
}

# ── Shipping tier patterns ────────────────────────────────────────────────────
SHIPPING_TIER_PATTERNS = [
    (r"(?i)^hemat kargo", "hemat_kargo"),
    (r"(?i)^hemat", "hemat"),
    (r"(?i)^reguler \(cashless\)", "reguler_cashless"),
    (r"(?i)^reguler", "reguler"),
    (r"(?i)^instant.*versi lama", "instant_legacy"),
    (r"(?i)^instant", "instant"),
    (r"(?i)^same day", "same_day"),
    (r"(?i)^agen", "agen"),
    (r"(?i)^kargo", "kargo"),
    (r"(?i)^express", "express"),
]

SHIPPING_COURIER_PATTERNS = [
    (r"(?i)spx", "SPX"),
    (r"(?i)j&t|jnt", "J&T"),
    (r"(?i)jne", "JNE"),
    (r"(?i)sicepat|si cepat", "SiCepat"),
    (r"(?i)anteraja", "Anteraja"),
    (r"(?i)lion|parcel", "Lion Parcel"),
    (r"(?i)ninja", "Ninja Express"),
    (r"(?i)pos indonesia|pos$", "Pos Indonesia"),
]

# ── Province standardization ─────────────────────────────────────────────────
PROVINCE_CORRECTIONS = {
    "DI YOGYAKARTA": "DI YOGYAKARTA",
    "D.I. YOGYAKARTA": "DI YOGYAKARTA",
    "DAERAH ISTIMEWA YOGYAKARTA": "DI YOGYAKARTA",
    "DKI JAKARTA": "DKI JAKARTA",
    "JAKARTA": "DKI JAKARTA",
    "KALIMANTAN UTARA": "KALIMANTAN UTARA",
}

JAVA_BALI_PROVINCES = {
    "DKI JAKARTA", "JAWA BARAT", "JAWA TENGAH", "JAWA TIMUR",
    "BANTEN", "DI YOGYAKARTA", "BALI",
}

REGION_MAP = {
    "DKI JAKARTA": "Jawa-Bali",
    "JAWA BARAT": "Jawa-Bali",
    "JAWA TENGAH": "Jawa-Bali",
    "JAWA TIMUR": "Jawa-Bali",
    "BANTEN": "Jawa-Bali",
    "DI YOGYAKARTA": "Jawa-Bali",
    "BALI": "Jawa-Bali",
    "SUMATERA UTARA": "Sumatera",
    "SUMATERA BARAT": "Sumatera",
    "SUMATERA SELATAN": "Sumatera",
    "RIAU": "Sumatera",
    "KEPULAUAN RIAU": "Sumatera",
    "JAMBI": "Sumatera",
    "BENGKULU": "Sumatera",
    "LAMPUNG": "Sumatera",
    "ACEH": "Sumatera",
    "BANGKA BELITUNG": "Sumatera",
    "KALIMANTAN BARAT": "Kalimantan",
    "KALIMANTAN TENGAH": "Kalimantan",
    "KALIMANTAN SELATAN": "Kalimantan",
    "KALIMANTAN TIMUR": "Kalimantan",
    "KALIMANTAN UTARA": "Kalimantan",
    "SULAWESI UTARA": "Sulawesi",
    "SULAWESI TENGAH": "Sulawesi",
    "SULAWESI SELATAN": "Sulawesi",
    "SULAWESI TENGGARA": "Sulawesi",
    "SULAWESI BARAT": "Sulawesi",
    "GORONTALO": "Sulawesi",
    "NUSA TENGGARA BARAT": "Nusa Tenggara",
    "NUSA TENGGARA TIMUR": "Nusa Tenggara",
    "MALUKU": "Maluku-Papua",
    "MALUKU UTARA": "Maluku-Papua",
    "PAPUA": "Maluku-Papua",
    "PAPUA BARAT": "Maluku-Papua",
    "PAPUA TENGAH": "Maluku-Papua",
    "PAPUA PEGUNUNGAN": "Maluku-Papua",
    "PAPUA SELATAN": "Maluku-Papua",
    "PAPUA BARAT DAYA": "Maluku-Papua",
}


def _parse_year_month_from_source(source_file: str) -> str:
    """Extract YYYY-MM string from source_file name like 'AprilSales2024.xlsx'."""
    month_map = {
        "january": "01", "februari": "02", "february": "02",
        "march": "03", "maret": "03", "april": "04",
        "may": "05", "mei": "05", "june": "06", "juni": "06",
        "july": "07", "juli": "07", "august": "08", "agustus": "08",
        "september": "09", "october": "10", "oktober": "10",
        "november": "11", "december": "12", "desember": "12",
    }
    if pd.isna(source_file):
        return None
    s = str(source_file).lower()
    year_match = re.search(r"(202[3-9])", s)
    year = year_match.group(1) if year_match else None
    month = None
    for name, num in month_map.items():
        if name in s:
            month = num
            break
    if year and month:
        return f"{year}-{month}"
    return None


def _normalize_status(raw_status: str) -> str:
    """Normalize Status Pesanan to clean analytical values."""
    if pd.isna(raw_status):
        return "unknown"
    s = str(raw_status).strip()
    if s in STATUS_MAP:
        return STATUS_MAP[s]
    # Long-form return-window statuses
    if "pesanan diterima" in s.lower() or "pembeli masih dapat mengajukan" in s.lower():
        return "completed_review"
    return "other"


def _parse_cancellation(reason: str) -> tuple:
    """Parse cancellation reason into (initiator, reason_clean)."""
    if pd.isna(reason) or str(reason).strip() == "":
        return (None, None)
    s = str(reason).strip()

    # Determine initiator
    initiator = "unknown"
    for pattern, label in CANCEL_INITIATOR_PATTERNS:
        if re.search(pattern, s):
            initiator = label
            break

    # Determine clean reason
    reason_clean = "other"
    for pattern, label in CANCEL_REASON_MAP.items():
        if re.search(pattern, s):
            reason_clean = label
            break

    return (initiator, reason_clean)


def _parse_shipping(option: str) -> tuple:
    """Parse Opsi Pengiriman into (shipping_tier, shipping_courier)."""
    if pd.isna(option):
        return ("unknown", "unknown")
    s = str(option).strip()

    # Tier
    tier = "other"
    for pattern, label in SHIPPING_TIER_PATTERNS:
        if re.match(pattern, s):
            tier = label
            break

    # Courier
    courier = "other"
    for pattern, label in SHIPPING_COURIER_PATTERNS:
        if re.search(pattern, s):
            courier = label
            break

    return (tier, courier)


def run_staging(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all staging transformations to the raw DataFrame.
    Returns clean staged DataFrame.
    """
    logger.info("Starting staging pipeline...")
    stg = df.copy()

    # ── 1. Parse order_datetime ───────────────────────────────────────────────
    logger.info("  Parsing timestamps...")
    stg["order_datetime"] = pd.to_datetime(stg["Waktu Pesanan Dibuat"], errors="coerce")

    # ── 2. Recover year_month_str from source_file for missing timestamps ─────
    logger.info("  Recovering missing timestamps from source_file...")
    stg["year_month_str"] = stg["order_datetime"].dt.strftime("%Y-%m")
    mask_missing_dt = stg["order_datetime"].isna()
    stg.loc[mask_missing_dt, "year_month_str"] = stg.loc[mask_missing_dt, "source_file"].apply(
        _parse_year_month_from_source
    )
    recovered = int(mask_missing_dt.sum() - stg["year_month_str"].isna().sum())
    logger.info(f"  Recovered {recovered:,} month labels from source_file")

    # ── 3. Normalize Status Pesanan ───────────────────────────────────────────
    logger.info("  Normalizing order status...")
    stg["status_normalized"] = stg["Status Pesanan"].apply(_normalize_status)

    # ── 4. Parse cancellation reason ─────────────────────────────────────────
    logger.info("  Parsing cancellation reasons...")
    cancel_parsed = stg["Alasan Pembatalan"].apply(_parse_cancellation)
    stg["cancellation_initiator"] = cancel_parsed.apply(lambda x: x[0])
    stg["cancellation_reason_clean"] = cancel_parsed.apply(lambda x: x[1])

    # ── 5. Parse shipping option ──────────────────────────────────────────────
    logger.info("  Parsing shipping options...")
    shipping_parsed = stg["Opsi Pengiriman"].apply(_parse_shipping)
    stg["shipping_tier"] = shipping_parsed.apply(lambda x: x[0])
    stg["shipping_courier"] = shipping_parsed.apply(lambda x: x[1])

    # ── 6. Standardize province names ────────────────────────────────────────
    logger.info("  Standardizing province names...")
    stg["province_clean"] = stg["Provinsi"].str.strip().str.upper()
    stg["province_clean"] = stg["province_clean"].replace(PROVINCE_CORRECTIONS)

    # ── 7. Parse city type (KOTA vs KAB) ─────────────────────────────────────
    stg["city_clean"] = stg["Kota/Kabupaten"].str.strip().str.upper()
    stg["city_type"] = stg["city_clean"].apply(
        lambda x: "KOTA" if str(x).startswith("KOTA") else "KAB" if str(x).startswith("KAB") else "OTHER"
    )

    # ── 8. Add region grouping ────────────────────────────────────────────────
    stg["region_group"] = stg["province_clean"].map(REGION_MAP).fillna("Other")
    stg["java_bali_flag"] = stg["province_clean"].isin(JAVA_BALI_PROVINCES).astype(int)

    # ── 9. Rename columns for consistency ────────────────────────────────────
    stg = stg.rename(columns={
        "Total Diskon": "total_diskon",
        "Status Pesanan": "status_raw",
        "Alasan Pembatalan": "alasan_pembatalan_raw",
        "Opsi Pengiriman": "opsi_pengiriman_raw",
        "Metode Pembayaran": "metode_pembayaran",
        "Kota/Kabupaten": "kota_kabupaten",
        "Provinsi": "provinsi_raw",
        "Ongkos Kirim Dibayar oleh Pembeli": "ongkir_dibayar_pembeli",
        "Estimasi Potongan Biaya Pengiriman": "estimasi_potongan_ongkir",
        "Total Pembayaran": "total_pembayaran",
        "Perkiraan Ongkos Kirim": "perkiraan_ongkir",
        "Waktu Pesanan Dibuat": "waktu_pesanan_raw",
    })

    logger.info(f"Staging complete: {len(stg):,} rows, {stg.shape[1]} columns")
    return stg


def save_staging(stg: pd.DataFrame, output_dir: str = STAGING_PATH) -> str:
    """Save staged DataFrame to parquet."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "stg_orders.parquet")
    stg.to_parquet(path, index=False, engine="pyarrow")
    logger.info(f"Staging data saved: {path} ({os.path.getsize(path)/1024:.1f} KB)")
    return path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from src.ingestion.ingest import load_raw
    from src.validation.validate import validate, print_report

    df = load_raw()
    report = validate(df)
    print_report(report)

    if report["summary"]["failed"] > 0:
        logger.error("Validation FAILED — fix critical issues before staging.")
        sys.exit(1)

    stg = run_staging(df)
    save_staging(stg)

    logger.info("Staging pipeline complete.")
    logger.info(f"  Status distribution:\n{stg['status_normalized'].value_counts().to_string()}")
    logger.info(f"  Shipping tier dist:\n{stg['shipping_tier'].value_counts().head(8).to_string()}")
    logger.info(f"  Region dist:\n{stg['region_group'].value_counts().to_string()}")
