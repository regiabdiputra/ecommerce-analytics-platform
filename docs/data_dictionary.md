# Data Dictionary
## Indonesia E-Commerce Sales & Shipping 2023–2025

**Project:** Intelligent Sales & Operations Analytics Platform  
**Dataset:** Indonesia E-Commerce Transactional Data  
**Coverage:** December 2023 – November 2025 (24 months)  
**Primary File:** `data/raw/all_months_clean.csv`  
**Last Updated:** Based on actual data inspection — no fabricated fields

---

## Dataset Grain

> **One row = One unique order transaction**

Verified: `order_id` is 100% unique across all 20,848 rows. No composite key needed.

---

## Column Definitions

### 1. `order_id`
| Attribute | Value |
|-----------|-------|
| Data Type | string |
| Nullable | No |
| Unique | Yes (100%) |
| Example | `ORD_0000001` |
| Missing % | 0.0% |
| Analytical Role | Primary Key |

**Business Meaning:** Anonymized unique identifier for each order transaction. Format is sequential (`ORD_XXXXXXX`). Cannot be traced back to real customer or order.

---

### 2. `total_qty`
| Attribute | Value |
|-----------|-------|
| Data Type | int64 |
| Nullable | No |
| Min / Max | 1 / 256 |
| Median | 1 |
| Mean | 2.6 |
| Missing % | 0.0% |
| Analytical Role | Measure — Order Volume |

**Business Meaning:** Total number of individual items (units) in the order across all product categories. An order with `total_qty=256` represents a bulk/wholesale purchase.

**Quality Note:** Values above 99th percentile (≥15 units) may represent bulk orders — should not be treated as outliers/errors but flagged for segmentation analysis.

---

### 3. `total_weight_gr`
| Attribute | Value |
|-----------|-------|
| Data Type | int64 |
| Nullable | No |
| Unit | Grams (gr) |
| Min / Max | 10 / 375,000 |
| Median | 500 |
| Mean | 2,005 |
| Missing % | 0.0% |
| Analytical Role | Measure — Operational / Shipping |

**Business Meaning:** Total shipment weight in grams for the entire order. Used by the shipping carrier to calculate shipping fees. Median of 500gr suggests most orders are lightweight (single small plastic item).

**Quality Note:** Max 375,000gr (375kg) is extreme — requires investigation. Likely bulk wholesale order.

---

### 4. `total_returned_qty`
| Attribute | Value |
|-----------|-------|
| Data Type | int64 |
| Nullable | No |
| Min / Max | 0 / 70 |
| Zeros | ~20,500+ (98.3%) |
| Missing % | 0.0% |
| Analytical Role | Measure — Returns |

**Business Meaning:** Number of units returned by the buyer after order completion. Extremely rare in this dataset (98.3% = 0). When non-zero, indicates post-delivery return/refund case.

**Analytical Limitation:** Near-zero variance makes this column unsuitable for return rate analysis at meaningful scale.

---

### 5. `Total Diskon`
| Attribute | Value |
|-----------|-------|
| Data Type | int64 |
| Nullable | No |
| Unit | IDR (Rupiah) |
| Min / Max | 0 / 700,000 |
| Zeros | 20,713 (99.4%) |
| Missing % | 0.0% |
| Analytical Role | Measure — Commercial / Discount |

**Business Meaning:** Total discount amount applied to the order in Indonesian Rupiah. Includes platform vouchers, seller discounts, and promotional discounts. 99.4% of orders have zero discount — discount-based analysis is limited.

---

### 6. `product_categories`
| Attribute | Value |
|-----------|-------|
| Data Type | string |
| Nullable | No |
| Unique raw combinations | 679 |
| Distinct individual categories | 38 |
| Format | Single value OR comma-separated multi-value |
| Missing % | 0.0% |
| Analytical Role | Dimension — Product |

**Business Meaning:** Product category or categories purchased in this order. When an order contains multiple product categories, values are comma-separated (e.g., `"Celengan, Keranjang, Tempat Nasi"`). Products are household plastic items (kitchen, storage, bathroom accessories).

**Derived transformation required:** Must be exploded (split by `, `) for category-level analysis.

**Top categories (verified from data):**
- Celengan (piggy bank / container)
- Mangkok Sambal / Saus
- Aksesoris Pintu
- Nampan / Tray
- Other, Baskom / Mangkok Besar, Keranjang, Seal / Baut / Roof

---

### 7. `num_product_categories`
| Attribute | Value |
|-----------|-------|
| Data Type | int64 |
| Nullable | No |
| Min / Max | 1 / 11 |
| Median | 1 |
| Mean | 1.11 |
| Missing % | 0.0% |
| Analytical Role | Measure — Order Complexity |

**Business Meaning:** Count of distinct product categories in the order. Derived from `product_categories`. Most orders (>90%) contain items from a single category. Value >1 indicates a multi-category basket order.

---

### 8. `Status Pesanan`
| Attribute | Value |
|-----------|-------|
| Data Type | string |
| Nullable | No |
| Unique values | 11 |
| Missing % | 0.0% |
| Analytical Role | Dimension — Order Status |

**Business Meaning:** Current status of the order. Primary analytical values:

| Raw Value | Count | % | Normalized Status |
|-----------|-------|---|-------------------|
| `Selesai` | 17,768 | 85.2% | `completed` |
| `Batal` | 2,830 | 13.6% | `cancelled` |
| `Sedang Dikirim` | 59 | 0.3% | `in_transit` |
| `Telah Dikirim` | 30 | 0.1% | `shipped` |
| `Pesanan diterima, namun Pembeli masih...` | 161 | 0.8% | `completed_review` |

**Quality Note:** The 161 "Pesanan diterima, namun..." entries are November 2025 orders still within the buyer return window. These are functionally completed orders and will be normalized to `completed_review` in staging.

---

### 9. `Alasan Pembatalan`
| Attribute | Value |
|-----------|-------|
| Data Type | string |
| Nullable | Yes — by design |
| Non-null count | 2,830 |
| Missing % | 86.4% |
| Analytical Role | Dimension — Cancellation Reason |

**Business Meaning:** Reason for order cancellation. NULL for all non-cancelled orders — this is expected and correct. Only populated when `Status Pesanan = 'Batal'`.

**Top cancellation reasons (verified):**
| Reason (summarized) | Count | % of cancelled |
|---------------------|-------|----------------|
| Buyer — changed mind / other | 662 | 23.4% |
| Buyer — wants to modify order | 558 | 19.7% |
| System — order not paid | 447 | 15.8% |
| Buyer — wrong address | 306 | 10.8% |
| System — shipping failed | 255 | 9.0% |
| System — seller late to ship | 113 | 4.0% |

**Derived transformation:** Will be parsed into `cancellation_initiator` (Buyer / System / Seller) and `cancellation_reason_clean`.

---

### 10. `Opsi Pengiriman`
| Attribute | Value |
|-----------|-------|
| Data Type | string |
| Nullable | No |
| Unique values | 45 |
| Missing % | 0.0% |
| Analytical Role | Dimension — Shipping |

**Business Meaning:** Shipping option selected by buyer. Format combines tier and courier: `"{Tier}-{Courier}"` (e.g., `"Hemat Kargo-SPX Hemat"`). 45 unique values arise from combinations.

**Top values:**
| Value | Count | % |
|-------|-------|---|
| Hemat Kargo-SPX Hemat | 12,597 | 60.4% |
| Reguler (Cashless)-SPX Standard | 4,622 | 22.2% |
| Others (43 more) | 3,629 | 17.4% |

**Derived transformation:** Will be parsed into:
- `shipping_tier`: Hemat / Reguler / Instant / Same Day / Kargo / Agen
- `shipping_courier`: SPX / JNE / J&T / SiCepat / others

---

### 11. `Metode Pembayaran`
| Attribute | Value |
|-----------|-------|
| Data Type | string |
| Nullable | No |
| Unique values | 12 |
| Missing % | 0.0% |
| Analytical Role | Dimension — Payment |

**Business Meaning:** Payment method used for the order.

| Payment Method | Count | % |
|----------------|-------|---|
| COD (Bayar di Tempat) | 11,538 | 55.3% |
| Saldo ShopeePay | 3,692 | 17.7% |
| Online Payment | 3,170 | 15.2% |
| SPayLater | 1,485 | 7.1% |
| SeaBank Bayar Instan | 637 | 3.1% |
| Kartu Kredit/Debit | 222 | 1.1% |
| Others (6 methods) | 104 | 0.5% |

**Business Implication:** COD dominance (55.3%) is critical for operations — COD orders are more susceptible to cancellation on delivery.

---

### 12. `Kota/Kabupaten`
| Attribute | Value |
|-----------|-------|
| Data Type | string |
| Nullable | No |
| Unique values | 424 |
| Missing % | 0.0% |
| Analytical Role | Dimension — Geography (City) |

**Business Meaning:** Destination city (`KOTA`) or regency (`KAB.`) for the order shipment. All values are in uppercase. Covers 424 distinct administrative areas across Indonesia.

**Format pattern:** `KOTA {name}` for municipalities, `KAB. {name}` for regencies.

---

### 13. `Provinsi`
| Attribute | Value |
|-----------|-------|
| Data Type | string |
| Nullable | No |
| Unique values | 34 |
| Missing % | 0.0% |
| Analytical Role | Dimension — Geography (Province) |

**Business Meaning:** Destination province for the order. Covers all 34 provinces of Indonesia (as of data collection period). All uppercase.

**Top 5 by volume:**
| Province | Orders | % |
|----------|--------|---|
| JAWA BARAT | 6,664 | 32.0% |
| BANTEN | 3,617 | 17.3% |
| DKI JAKARTA | 2,899 | 13.9% |
| JAWA TIMUR | 1,599 | 7.7% |
| JAWA TENGAH | 1,496 | 7.2% |

---

### 14. `Ongkos Kirim Dibayar oleh Pembeli`
| Attribute | Value |
|-----------|-------|
| Data Type | int64 |
| Nullable | No |
| Unit | IDR (Rupiah) |
| Min / Max | 0 / 584,000 |
| Median | 0 |
| Mean | 4,190 |
| Zeros | 14,552 (69.8%) |
| Missing % | 0.0% |
| Analytical Role | Measure — Shipping Revenue |

**Business Meaning:** Actual shipping fee charged to and paid by the buyer. A value of 0 means the buyer received free shipping (platform or seller absorbed the cost). 69.8% of orders = free shipping for buyer.

---

### 15. `Estimasi Potongan Biaya Pengiriman`
| Attribute | Value |
|-----------|-------|
| Data Type | int64 |
| Nullable | No |
| Unit | IDR (Rupiah) |
| Min / Max | 0 / 312,000 |
| Median | 9,500 |
| Mean | 10,723 |
| Zeros | 5,309 (25.5%) |
| Missing % | 0.0% |
| Analytical Role | Measure — Shipping Subsidy |

**Business Meaning:** Estimated shipping subsidy or discount provided by the platform (Shopee). This is the amount deducted from the full shipping cost that the buyer does not pay. High median (9,500 IDR) indicates significant platform subsidy per order.

**Derived metric:** `shipping_subsidy_ratio = Estimasi Potongan / Perkiraan Ongkos Kirim`

---

### 16. `Total Pembayaran`
| Attribute | Value |
|-----------|-------|
| Data Type | int64 |
| Nullable | No |
| Unit | IDR (Rupiah) |
| Min / Max | 0 / 3,403,591 |
| Median | 21,800 |
| Mean | 50,684 |
| Zeros | 2,892 (13.9%) |
| Missing % | 0.0% |
| Analytical Role | Measure — Revenue Proxy |

**Business Meaning:** Total payment amount received for the order including product price and any buyer-paid shipping. For cancelled orders, this is 0 (no payment collected). This is the closest variable to "revenue" in this dataset.

**Important caveat:** This is total buyer payment, not seller net revenue. Platform fees and cost of goods are not available.

**Quality note:** 62 completed orders have `Total Pembayaran = 0` — likely full voucher/subsidy coverage. These are valid transactions.

---

### 17. `Perkiraan Ongkos Kirim`
| Attribute | Value |
|-----------|-------|
| Data Type | int64 |
| Nullable | No |
| Unit | IDR (Rupiah) |
| Min / Max | 1 / 959,200 |
| Median | 11,000 |
| Mean | 18,426 |
| Zeros | 0 |
| Missing % | 0.0% |
| Analytical Role | Measure — Shipping Cost |

**Business Meaning:** Full estimated shipping cost for the order before any subsidy. This represents what the shipping carrier charges in total. The difference between this and `Ongkos Kirim Dibayar oleh Pembeli` is absorbed by the platform/seller.

**Key relationship:**  
`Perkiraan Ongkos Kirim ≈ Ongkos Kirim Dibayar Pembeli + Estimasi Potongan Biaya Pengiriman`

---

### 18. `Waktu Pesanan Dibuat`
| Attribute | Value |
|-----------|-------|
| Data Type | string → datetime |
| Format | `YYYY-MM-DD HH:MM` |
| Nullable | Yes |
| Min / Max | 2023-12-01 / 2025-11-30 |
| Missing % | 9.5% (1,980 rows) |
| Analytical Role | Dimension — Time |

**Business Meaning:** Timestamp when the order was created by the buyer. Used for time-series analysis, monthly aggregation, and trend analysis.

**Quality note:** 1,980 missing timestamps primarily from December 2024 and July 2025 monthly files where the original Excel did not include timestamp data. Month can be recovered from `source_file` for these rows.

---

### 19. `source_file`
| Attribute | Value |
|-----------|-------|
| Data Type | string |
| Nullable | No |
| Unique values | 24 |
| Missing % | 0.0% |
| Analytical Role | Metadata / Fallback Time Dimension |

**Business Meaning:** Name of the source Excel file from which this row was consolidated. Format: `{Month}{Year}Sales.xlsx` (e.g., `AprilSales2024.xlsx`). Added during the consolidation process. Used as fallback for month/year extraction when `Waktu Pesanan Dibuat` is missing.

---

## Derived Columns (To Be Created in Transformation)

| Derived Column | Formula | Purpose |
|----------------|---------|---------|
| `order_date` | `pd.to_datetime(Waktu Pesanan Dibuat)` | Clean datetime |
| `order_year` | `order_date.dt.year` | Annual grouping |
| `order_month` | `order_date.dt.month` | Monthly grouping |
| `order_month_name` | `order_date.dt.month_name()` | Display label |
| `order_quarter` | `order_date.dt.quarter` | Quarterly grouping |
| `order_week` | `order_date.dt.isocalendar().week` | Weekly grouping |
| `order_hour` | `order_date.dt.hour` | Intraday analysis |
| `year_month` | `order_date.dt.to_period('M')` | Time-series key |
| `year_month_str` | `YYYY-MM` string from source_file fallback | Robust month key |
| `is_cancelled` | `1 if Status Pesanan == 'Batal' else 0` | Cancellation flag |
| `is_completed` | `1 if status_normalized in [completed, completed_review] else 0` | Completion flag |
| `status_normalized` | Mapped from raw `Status Pesanan` | Clean status |
| `cancellation_initiator` | Parsed from `Alasan Pembatalan` | Who cancelled |
| `cancellation_reason_clean` | Parsed from `Alasan Pembatalan` | Clean reason |
| `shipping_tier` | Parsed from `Opsi Pengiriman` (before `-`) | Hemat/Reguler/etc |
| `shipping_courier` | Parsed from `Opsi Pengiriman` (after `-`) | SPX/JNE/J&T/etc |
| `shipping_cost_buyer_ratio` | `Ongkos Kirim Dibayar / Perkiraan Ongkos Kirim` | Buyer share |
| `shipping_subsidy_ratio` | `Estimasi Potongan / Perkiraan Ongkos Kirim` | Subsidy share |
| `weight_kg` | `total_weight_gr / 1000` | Weight in kg |
| `is_multi_category` | `1 if num_product_categories > 1 else 0` | Multi-cat flag |
| `has_discount` | `1 if Total Diskon > 0 else 0` | Discount flag |
| `is_cod` | `1 if Metode Pembayaran == 'COD...' else 0` | COD flag |
| `province_clean` | Standardized province name | Consistent geo key |
| `city_type` | `KOTA` or `KAB` from prefix | City classification |
| `java_bali_flag` | 1 if Jawa/Bali/Banten province | Core market flag |

---

## Variables NOT Available (Analytical Limitations)

| Variable | Reason Unavailable | Impact |
|----------|--------------------|--------|
| Customer ID | Anonymized / not provided | Cannot do customer-level analysis, RFM, CLV |
| Product SKU / Name | Not in dataset | Cannot do product-level analysis |
| Seller ID | Not provided | Cannot analyze seller performance |
| Delivery timestamp | Only order creation time | Cannot compute delivery duration or SLA |
| Cost of Goods (COGS) | Not provided | Cannot compute profit margin |
| Platform fees | Not provided | Cannot compute net revenue |
| Return reason | Not in dataset | Cannot analyze return drivers |
| Buyer location (origin) | Not provided | Only destination geography |

---

## Data Relationships

```
fact_orders (grain: 1 row = 1 order)
    │
    ├── dim_date         (via order_date / year_month_str)
    ├── dim_geography    (via Provinsi + Kota/Kabupaten)
    ├── dim_product_category (via product_categories — exploded)
    ├── dim_payment      (via Metode Pembayaran)
    ├── dim_shipping     (via Opsi Pengiriman → tier + courier)
    └── dim_status       (via status_normalized)
```
