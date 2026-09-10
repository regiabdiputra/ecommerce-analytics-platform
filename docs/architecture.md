# Architecture Documentation
## Intelligent Sales & Operations Analytics Platform

**Project:** Indonesia E-Commerce Analytics — December 2023 to November 2025  
**Architecture Style:** Medallion (Raw → Staging → Processed → Marts)  
**Execution:** Local, fully open-source, no paid services

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                  │
│  archive (2).zip                                                      │
│  ├── all_months_clean.csv  (primary — 20,848 rows, 19 cols)          │
│  ├── Clean_Dataset/CLEAN/  (24 monthly xlsx — preserved reference)   │
│  └── RAW_PUBLIC_Dataset/   (24 monthly xlsx — preserved reference)   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 0: DATA INGESTION                           │
│  src/ingestion/ingest.py                                             │
│  • Read CSV (sep=';', encoding='utf-8-sig')                          │
│  • Preserve raw — no modifications                                   │
│  • Write to data/raw/all_months_clean.csv                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PHASE 1: DATA VALIDATION                           │
│  src/validation/validate.py                                          │
│  • Schema validation (column names, dtypes)                          │
│  • Type validation (numeric, string, datetime)                       │
│  • Duplicate detection                                               │
│  • Missing value analysis                                            │
│  • Business rule checks (no negative qty/weight/price)               │
│  • Categorical consistency checks                                    │
│  • Geographic consistency checks                                     │
│  • Outputs: validation_report.json                                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  PHASE 2: STAGING LAYER                              │
│  src/transformation/staging.py                                       │
│  • Normalize Status Pesanan → status_normalized                      │
│  • Parse Alasan Pembatalan → cancellation_initiator + reason_clean   │
│  • Parse Opsi Pengiriman → shipping_tier + shipping_courier          │
│  • Parse Waktu Pesanan Dibuat → order_datetime                       │
│  • Recover missing months from source_file                           │
│  • Standardize province/city strings                                 │
│  • Output: data/staging/stg_orders.parquet                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                PHASE 3: TRANSFORMATION LAYER                         │
│  src/transformation/transform.py                                     │
│  • Derive time features (year, month, quarter, week, hour)           │
│  • Derive flags (is_cancelled, is_completed, is_cod, has_discount)   │
│  • Derive ratios (shipping_cost_ratio, subsidy_ratio)                │
│  • Derive weight_kg, city_type, java_bali_flag                       │
│  • Create category-exploded view for category analysis               │
│  • Output: data/processed/orders_enriched.parquet                    │
│            data/processed/orders_categories.parquet                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│               PHASE 4: DIMENSIONAL MODEL (MARTS)                     │
│  src/modeling/build_model.py                                         │
│                                                                      │
│  fact_orders           ← central fact table (order grain)            │
│  dim_date              ← calendar dimension                          │
│  dim_geography         ← province + city hierarchy                   │
│  dim_product_category  ← 38 product categories                       │
│  dim_payment           ← 12 payment methods                          │
│  dim_shipping          ← tier + courier                              │
│  dim_status            ← normalized order status                     │
│                                                                      │
│  Output: data/marts/*.parquet                                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 5: KPI LAYER                                │
│  src/analytics/kpi.py                                                │
│  • Total Orders, Completed Orders, Cancelled Orders                  │
│  • Cancellation Rate                                                 │
│  • Total Revenue (Total Pembayaran — completed orders)               │
│  • Average Order Value                                               │
│  • Total Quantity, Avg Qty per Order                                 │
│  • Total Shipping Cost, Avg Shipping Cost per Order                  │
│  • Shipping Subsidy Rate                                             │
│  • MoM Growth, YoY Comparison                                        │
│  • Category Contribution, Regional Contribution                      │
│  Output: outputs/reports/kpi_summary.json                            │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    PHASE 6–9: ANALYTICS MODULES                      │
│                                                                       │
│  src/analytics/sales_analytics.py                                    │
│  • Monthly trend, category performance, regional performance         │
│  • Growth rates, Pareto analysis, concentration metrics              │
│                                                                       │
│  src/analytics/operations_analytics.py                               │
│  • Cancellation analysis (rate, reasons, geography, payment)         │
│  • Shipping cost analysis, weight distribution                        │
│  • Operational anomalies by region/category                          │
│                                                                       │
│  src/analytics/geo_analytics.py                                      │
│  • Province/city distribution, performance, risk segmentation        │
│  • Regional contribution, cancellation rate by geography             │
│                                                                       │
│  src/analytics/segmentation.py                                       │
│  • Region quadrant: High/Low Volume × High/Low Growth                │
│  • Category strategic quadrant                                       │
└──────────────┬───────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  PHASE 10: FORECASTING MODULE                        │
│  src/forecasting/forecaster.py                                       │
│  • Target: monthly order volume (24 observations)                    │
│  • Models: Naive, Moving Average, ETS, Holt-Winters, ARIMA, SARIMA   │
│  • Validation: expanding window cross-validation                     │
│  • Metrics: MAE, RMSE, sMAPE                                         │
│  • Output: 3-month forecast + prediction interval                    │
│  Output: outputs/forecasts/forecast_results.json                     │
└──────────────┬───────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│               PHASE 11: ANOMALY DETECTION                            │
│  src/monitoring/anomaly_detection.py                                 │
│  • Rolling z-score on monthly order volume                           │
│  • IQR-based detection on shipping cost                              │
│  • STL decomposition residuals for cancellation rate                 │
│  • Severity levels: Normal / Watch / Warning / Critical              │
│  Output: outputs/reports/anomaly_report.json                         │
└──────────────┬───────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│               PHASE 12: EARLY WARNING SYSTEM                         │
│  src/monitoring/early_warning.py                                     │
│  • Rule-based alert engine                                           │
│  • Cancellation rate spike detection                                 │
│  • Regional volume decline detection                                 │
│  • Shipping cost anomaly detection                                   │
│  • COD cancellation rate monitoring                                  │
│  Output: outputs/reports/early_warning_alerts.json                   │
└──────────────┬───────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│               PHASE 13: DECISION SUPPORT ENGINE                      │
│  src/analytics/decision_support.py                                   │
│  • Evidence-based recommendation framework                           │
│  • Observation → Evidence → Implication → Action → Priority          │
│  • Structured output for dashboard consumption                       │
│  Output: outputs/reports/recommendations.json                        │
└──────────────┬───────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│               PHASE 14: STREAMLIT DASHBOARD                          │
│  dashboard/app.py  (entry point)                                     │
│  dashboard/pages/                                                    │
│  ├── 1_executive_overview.py                                         │
│  ├── 2_sales_analytics.py                                            │
│  ├── 3_operations_analytics.py                                       │
│  ├── 4_geographic_analytics.py                                       │
│  ├── 5_forecasting.py                                                │
│  ├── 6_early_warning.py                                              │
│  └── 7_decision_support.py                                           │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Data Layer Definitions

### Layer 1: Raw (`data/raw/`)
- Source files, preserved exactly as received
- Never modified
- `all_months_clean.csv` — 20,848 rows, 19 columns, semicolon-separated

### Layer 2: Staging (`data/staging/`)
- Cleaned, typed, normalized version of raw
- No new analytical columns — only corrections
- Format: Parquet (columnar, fast I/O)
- File: `stg_orders.parquet`

### Layer 3: Processed (`data/processed/`)
- Enriched with derived features and flags
- Ready for analytical queries
- Files:
  - `orders_enriched.parquet` — one row per order with all derived features
  - `orders_categories.parquet` — exploded by category (one row per order-category pair)

### Layer 4: Marts (`data/marts/`)
- Star schema dimensional model
- Optimized for analytical queries
- Files: `fact_orders.parquet`, `dim_*.parquet`

---

## Dimensional Model

### fact_orders
| Column | Type | Description |
|--------|------|-------------|
| order_id | str | PK — unique order identifier |
| date_key | str | FK → dim_date (YYYY-MM-DD) |
| year_month_key | str | FK → dim_date (YYYY-MM) |
| geography_key | str | FK → dim_geography (province|city) |
| payment_key | str | FK → dim_payment |
| shipping_key | str | FK → dim_shipping |
| status_key | str | FK → dim_status |
| total_qty | int | Quantity ordered |
| total_weight_gr | int | Shipment weight (grams) |
| total_returned_qty | int | Returned quantity |
| total_diskon | int | Discount amount (IDR) |
| ongkir_dibayar_pembeli | int | Shipping paid by buyer (IDR) |
| estimasi_potongan_ongkir | int | Shipping subsidy (IDR) |
| total_pembayaran | int | Total payment (IDR) |
| perkiraan_ongkir | int | Full estimated shipping cost (IDR) |
| num_product_categories | int | Number of categories in order |
| is_cancelled | int | 0/1 flag |
| is_completed | int | 0/1 flag |
| is_cod | int | 0/1 flag |
| has_discount | int | 0/1 flag |
| is_multi_category | int | 0/1 flag |
| java_bali_flag | int | 0/1 — core market flag |
| weight_kg | float | Weight in kg |
| shipping_subsidy_ratio | float | Subsidy / full shipping cost |
| shipping_cost_buyer_ratio | float | Buyer paid / full shipping cost |

### dim_date
| Column | Description |
|--------|-------------|
| year_month_key (PK) | YYYY-MM |
| year | 4-digit year |
| month | 1-12 |
| month_name | January…December |
| quarter | Q1–Q4 |
| year_quarter | YYYY-Qn |
| is_peak_season | flag for Jul–Aug (observed peak) |

### dim_geography
| Column | Description |
|--------|-------------|
| geography_key (PK) | province\|city composite |
| province | Province name (uppercase) |
| city | City/regency name |
| city_type | KOTA or KAB |
| java_bali_flag | Core market indicator |
| region_group | Jawa-Bali / Sumatera / Kalimantan / Sulawesi / etc |

### dim_product_category
| Column | Description |
|--------|-------------|
| category_key (PK) | Normalized category name |
| category_name | Original category name |
| category_group | High-level grouping (Kitchen / Storage / Bathroom / Other) |

### dim_payment
| Column | Description |
|--------|-------------|
| payment_key (PK) | Normalized payment method |
| payment_method | Original method name |
| payment_type | Digital / COD / Credit / BNPL |
| is_cod | COD flag |

### dim_shipping
| Column | Description |
|--------|-------------|
| shipping_key (PK) | tier\|courier composite |
| shipping_tier | Hemat / Reguler / Instant / Same Day / Kargo / Agen |
| shipping_courier | SPX / JNE / J&T / SiCepat / etc |
| raw_option | Original `Opsi Pengiriman` value |

### dim_status
| Column | Description |
|--------|-------------|
| status_key (PK) | Normalized status code |
| status_normalized | completed / cancelled / in_transit / shipped / completed_review |
| status_raw | Original `Status Pesanan` value |
| is_terminal | 1 if final state (completed/cancelled) |

---

## Technology Stack

| Component | Tool | Version |
|-----------|------|---------|
| Language | Python | 3.12.1 |
| Data manipulation | pandas | 3.0.5 |
| Numerical computing | numpy | 2.2.6 |
| Statistical modeling | statsmodels | latest |
| ML / anomaly detection | scikit-learn | latest |
| Visualization | plotly | latest |
| Dashboard | streamlit | latest |
| File format | pyarrow / parquet | latest |
| Excel reading | openpyxl | 3.1.5 |
| Testing | pytest | latest |
| Database (optional) | DuckDB | latest |

All tools are free and open-source. No paid services required.

---

## Pipeline Execution Order

```
python src/ingestion/ingest.py          # Step 1 — load raw
python src/validation/validate.py       # Step 2 — validate
python src/transformation/staging.py   # Step 3 — stage
python src/transformation/transform.py # Step 4 — enrich
python src/modeling/build_model.py     # Step 5 — dimensional model
python src/analytics/kpi.py            # Step 6 — KPI layer
python src/analytics/sales_analytics.py
python src/analytics/operations_analytics.py
python src/analytics/geo_analytics.py
python src/analytics/segmentation.py
python src/forecasting/forecaster.py   # Step 7 — forecasting
python src/monitoring/anomaly_detection.py  # Step 8
python src/monitoring/early_warning.py      # Step 9
python src/analytics/decision_support.py   # Step 10
streamlit run dashboard/app.py             # Step 11 — dashboard

# Or run everything at once:
python run_pipeline.py
```
