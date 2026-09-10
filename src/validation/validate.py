"""
Validation module — comprehensive data quality checks on raw data.
Produces a validation report without modifying any data.
"""
import pandas as pd
import numpy as np
import json
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPORTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports")
)


def validate(df: pd.DataFrame) -> dict:
    """
    Run all validation checks on the raw DataFrame.
    Returns a structured validation report dict.
    Does NOT modify the DataFrame.
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_rows": len(df),
        "total_columns": df.shape[1],
        "checks": {},
        "summary": {"passed": 0, "warnings": 0, "failed": 0},
    }

    def add_check(name, status, detail, affected_rows=0):
        report["checks"][name] = {
            "status": status,  # PASS / WARN / FAIL
            "detail": detail,
            "affected_rows": affected_rows,
        }
        report["summary"][{"PASS": "passed", "WARN": "warnings", "FAIL": "failed"}[status]] += 1

    # ── 1. Schema validation ──────────────────────────────────────────────────
    expected = [
        "order_id", "total_qty", "total_weight_gr", "total_returned_qty",
        "Total Diskon", "product_categories", "num_product_categories",
        "Status Pesanan", "Alasan Pembatalan", "Opsi Pengiriman",
        "Metode Pembayaran", "Kota/Kabupaten", "Provinsi",
        "Ongkos Kirim Dibayar oleh Pembeli", "Estimasi Potongan Biaya Pengiriman",
        "Total Pembayaran", "Perkiraan Ongkos Kirim",
        "Waktu Pesanan Dibuat", "source_file",
    ]
    missing_cols = [c for c in expected if c not in df.columns]
    if missing_cols:
        add_check("schema_columns", "FAIL", f"Missing columns: {missing_cols}")
    else:
        add_check("schema_columns", "PASS", "All 19 expected columns present")

    # ── 2. Primary key uniqueness ─────────────────────────────────────────────
    dup_ids = int(df["order_id"].duplicated().sum())
    null_ids = int(df["order_id"].isna().sum())
    if dup_ids == 0 and null_ids == 0:
        add_check("primary_key", "PASS", f"order_id is 100% unique, 0 nulls")
    else:
        add_check("primary_key", "FAIL",
                  f"Duplicate order_ids: {dup_ids}, Null order_ids: {null_ids}",
                  affected_rows=dup_ids + null_ids)

    # ── 3. Full-row duplicates ────────────────────────────────────────────────
    full_dups = int(df.duplicated().sum())
    status = "PASS" if full_dups == 0 else "WARN"
    add_check("full_row_duplicates", status,
              f"Full-row duplicates: {full_dups}", affected_rows=full_dups)

    # ── 4. Missing value analysis ─────────────────────────────────────────────
    miss = df.isna().sum()
    miss_pct = (df.isna().mean() * 100).round(2)

    # Alasan Pembatalan — expected high missing (non-cancelled orders)
    cancel_mask = df["Status Pesanan"] == "Batal"
    n_cancelled = int(cancel_mask.sum())
    n_cancel_no_reason = int((cancel_mask & df["Alasan Pembatalan"].isna()).sum())
    add_check(
        "missing_alasan_pembatalan",
        "PASS" if n_cancel_no_reason == 0 else "WARN",
        f"Cancelled orders missing reason: {n_cancel_no_reason}/{n_cancelled}. "
        f"Non-cancelled missing: expected (86.4% is correct).",
        affected_rows=n_cancel_no_reason,
    )

    # Waktu Pesanan Dibuat — 9.5% missing is a known issue
    ts_missing = int(miss["Waktu Pesanan Dibuat"])
    ts_pct = float(miss_pct["Waktu Pesanan Dibuat"])
    add_check(
        "missing_timestamps",
        "WARN" if ts_missing > 0 else "PASS",
        f"Waktu Pesanan Dibuat missing: {ts_missing:,} ({ts_pct:.1f}%). "
        "Recoverable via source_file column.",
        affected_rows=ts_missing,
    )

    # All other columns should be 0 missing
    other_cols = [c for c in df.columns
                  if c not in ("Alasan Pembatalan", "Waktu Pesanan Dibuat")]
    unexpected_missing = {c: int(miss[c]) for c in other_cols if miss[c] > 0}
    if unexpected_missing:
        add_check("missing_other_columns", "FAIL",
                  f"Unexpected missing values: {unexpected_missing}",
                  affected_rows=sum(unexpected_missing.values()))
    else:
        add_check("missing_other_columns", "PASS",
                  "All non-nullable columns have 0 missing values")

    # ── 5. Numeric type validation ────────────────────────────────────────────
    numeric_cols = [
        "total_qty", "total_weight_gr", "total_returned_qty", "Total Diskon",
        "num_product_categories", "Ongkos Kirim Dibayar oleh Pembeli",
        "Estimasi Potongan Biaya Pengiriman", "Total Pembayaran",
        "Perkiraan Ongkos Kirim",
    ]
    non_numeric = [c for c in numeric_cols
                   if not pd.api.types.is_numeric_dtype(df[c])]
    if non_numeric:
        add_check("numeric_types", "FAIL", f"Non-numeric columns: {non_numeric}")
    else:
        add_check("numeric_types", "PASS", "All 9 numeric columns have correct types")

    # ── 6. Negative value checks ──────────────────────────────────────────────
    neg_checks = {
        "total_qty": (df["total_qty"] < 0).sum(),
        "total_weight_gr": (df["total_weight_gr"] < 0).sum(),
        "total_returned_qty": (df["total_returned_qty"] < 0).sum(),
        "Total Diskon": (df["Total Diskon"] < 0).sum(),
        "Ongkos Kirim Dibayar oleh Pembeli": (df["Ongkos Kirim Dibayar oleh Pembeli"] < 0).sum(),
        "Estimasi Potongan Biaya Pengiriman": (df["Estimasi Potongan Biaya Pengiriman"] < 0).sum(),
        "Total Pembayaran": (df["Total Pembayaran"] < 0).sum(),
        "Perkiraan Ongkos Kirim": (df["Perkiraan Ongkos Kirim"] < 0).sum(),
    }
    total_neg = sum(int(v) for v in neg_checks.values())
    if total_neg == 0:
        add_check("negative_values", "PASS", "No negative values in any numeric column")
    else:
        neg_detail = {k: int(v) for k, v in neg_checks.items() if v > 0}
        add_check("negative_values", "FAIL",
                  f"Negative values found: {neg_detail}", affected_rows=total_neg)

    # ── 7. Zero quantity check ────────────────────────────────────────────────
    zero_qty = int((df["total_qty"] == 0).sum())
    add_check("zero_quantity", "PASS" if zero_qty == 0 else "FAIL",
              f"Orders with total_qty=0: {zero_qty}", affected_rows=zero_qty)

    # ── 8. Business rule: cancelled orders payment = 0 ───────────────────────
    cancel_paid = int(
        ((df["Status Pesanan"] == "Batal") & (df["Total Pembayaran"] > 0)).sum()
    )
    add_check("cancelled_with_payment", "PASS" if cancel_paid == 0 else "WARN",
              f"Cancelled orders with Total Pembayaran > 0: {cancel_paid}",
              affected_rows=cancel_paid)

    # ── 9. Business rule: completed with zero payment ────────────────────────
    completed_statuses = ["Selesai"]
    selesai_zero = int(
        (df["Status Pesanan"].isin(completed_statuses) & (df["Total Pembayaran"] == 0)).sum()
    )
    add_check("completed_zero_payment", "WARN" if selesai_zero > 0 else "PASS",
              f"Completed orders with Total Pembayaran=0: {selesai_zero} "
              "(likely full voucher/promo coverage — valid)",
              affected_rows=selesai_zero)

    # ── 10. Date range validation ─────────────────────────────────────────────
    df_dates = pd.to_datetime(df["Waktu Pesanan Dibuat"], errors="coerce")
    valid_dates = df_dates.dropna()
    if len(valid_dates) > 0:
        date_min = valid_dates.min()
        date_max = valid_dates.max()
        future_dates = int((valid_dates > pd.Timestamp("2025-12-31")).sum())
        past_dates = int((valid_dates < pd.Timestamp("2023-01-01")).sum())
        if future_dates > 0 or past_dates > 0:
            add_check("date_range", "WARN",
                      f"Dates outside expected range: future={future_dates}, "
                      f"before_2023={past_dates}. Min={date_min}, Max={date_max}",
                      affected_rows=future_dates + past_dates)
        else:
            add_check("date_range", "PASS",
                      f"All timestamps within valid range: {date_min} → {date_max}")

    # ── 11. Categorical consistency — Status Pesanan ──────────────────────────
    known_statuses = {
        "Selesai", "Batal", "Sedang Dikirim", "Telah Dikirim",
    }
    status_vals = set(df["Status Pesanan"].dropna().unique())
    # Flag values that contain known substrings but are long-form (return window text)
    long_form = [v for v in status_vals
                 if len(v) > 30]  # "Pesanan diterima, namun..." type
    unexpected_status = [v for v in status_vals
                         if v not in known_statuses and len(v) <= 30]
    if unexpected_status:
        add_check("status_consistency", "WARN",
                  f"Unexpected short status values: {unexpected_status}. "
                  f"Long-form return-window statuses: {len(long_form)} variants (expected)")
    else:
        add_check("status_consistency", "PASS",
                  f"Status Pesanan: {len(status_vals)} unique values. "
                  f"{len(long_form)} are long-form return-window variants (expected for Nov 2025)")

    # ── 12. Geographic consistency ────────────────────────────────────────────
    n_provinces = int(df["Provinsi"].nunique())
    n_cities = int(df["Kota/Kabupaten"].nunique())
    null_prov = int(df["Provinsi"].isna().sum())
    null_city = int(df["Kota/Kabupaten"].isna().sum())
    add_check("geography_completeness", "PASS" if null_prov == 0 and null_city == 0 else "FAIL",
              f"Provinces: {n_provinces} unique, {null_prov} null. "
              f"Cities: {n_cities} unique, {null_city} null.")

    # ── 13. Shipping cost logic check ────────────────────────────────────────
    # Perkiraan Ongkos Kirim should be >= Ongkos Kirim Dibayar Pembeli
    shipping_inconsistent = int(
        (df["Perkiraan Ongkos Kirim"] < df["Ongkos Kirim Dibayar oleh Pembeli"]).sum()
    )
    add_check("shipping_cost_logic", "PASS" if shipping_inconsistent == 0 else "WARN",
              f"Orders where buyer paid more than estimated full shipping: {shipping_inconsistent}",
              affected_rows=shipping_inconsistent)

    # ── 14. Source file completeness ──────────────────────────────────────────
    n_source_files = int(df["source_file"].nunique())
    expected_files = 24  # Dec 2023 – Nov 2025
    add_check("source_file_count",
              "PASS" if n_source_files == expected_files else "WARN",
              f"Source files: {n_source_files} (expected {expected_files})")

    # ── 15. Extreme outlier flagging ──────────────────────────────────────────
    outlier_info = {}
    outlier_thresholds = {
        "total_qty": 100,
        "total_weight_gr": 100_000,
        "Total Pembayaran": 2_000_000,
        "Perkiraan Ongkos Kirim": 200_000,
    }
    for col, threshold in outlier_thresholds.items():
        n_above = int((df[col] > threshold).sum())
        if n_above > 0:
            outlier_info[col] = {"threshold": threshold, "count": n_above}
    if outlier_info:
        add_check("extreme_outliers", "WARN",
                  f"Extreme values detected (require investigation): {outlier_info}",
                  affected_rows=sum(v["count"] for v in outlier_info.values()))
    else:
        add_check("extreme_outliers", "PASS", "No extreme outliers detected")

    # ── Final summary ─────────────────────────────────────────────────────────
    logger.info(f"Validation complete: "
                f"{report['summary']['passed']} PASS, "
                f"{report['summary']['warnings']} WARN, "
                f"{report['summary']['failed']} FAIL")

    return report


def save_report(report: dict, output_dir: str = REPORTS_PATH) -> str:
    """Save validation report as JSON."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "validation_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"Validation report saved: {path}")
    return path


def print_report(report: dict) -> None:
    """Print a human-readable validation summary."""
    print("\n" + "=" * 65)
    print("  DATA VALIDATION REPORT")
    print("=" * 65)
    print(f"  Timestamp : {report['timestamp']}")
    print(f"  Rows      : {report['total_rows']:,}")
    print(f"  Columns   : {report['total_columns']}")
    s = report["summary"]
    print(f"  Result    : {s['passed']} PASS | {s['warnings']} WARN | {s['failed']} FAIL")
    print("-" * 65)
    for name, check in report["checks"].items():
        icon = {"PASS": "OK", "WARN": "! ", "FAIL": "XX"}[check["status"]]
        rows_note = f" [{check['affected_rows']:,} rows]" if check["affected_rows"] > 0 else ""
        print(f"  [{icon}] {name:<40} {check['status']}{rows_note}")
        if check["status"] != "PASS":
            print(f"       → {check['detail']}")
    print("=" * 65)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.ingestion.ingest import load_raw

    df = load_raw()
    report = validate(df)
    print_report(report)
    save_report(report)
