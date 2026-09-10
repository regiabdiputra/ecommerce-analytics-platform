# Platform Analitik Penjualan & Operasional E-Commerce Indonesia

**End-to-end analytics platform** untuk data transaksi e-commerce Indonesia periode Desember 2023 hingga November 2025.

---

## Ringkasan Project

Platform ini memproses **20.848 transaksi** dari **34 provinsi** dan **38 kategori produk** melalui pipeline data otomatis, kemudian menyajikannya dalam dashboard interaktif 7 halaman yang dapat dipahami oleh siapa saja — dari eksekutif hingga orang awam.

### Temuan Bisnis Kunci

- Total pendapatan **Rp 1,05 Miliar** selama 24 bulan dengan pertumbuhan volume 2,5x
- Tingkat pembatalan **13,57%** — **49% di antaranya** murni keputusan pembeli sendiri, bukan masalah logistik
- **80,2% pesanan** terkonsentrasi di Jawa-Bali — risiko konsentrasi signifikan
- Platform menanggung subsidi ongkir **Rp 384 juta** (36,5% dari total pendapatan)
- Sulawesi Tengah: tingkat batal **30,36%** vs rata-rata nasional 13,57% — sinyal kritis terdeteksi otomatis

---

## Demo

> **Live Dashboard**: [ecommerce-analytics.streamlit.app](https://regiabdiputra-ecommerce-analytics-platform.streamlit.app)

---

## Arsitektur & Tech Stack

```
data/raw/          →  src/ingestion/       →  data/staging/
                   →  src/validation/      →  data/processed/
                   →  src/transformation/  →  data/marts/
                   →  src/analytics/       →  outputs/reports/
                   →  src/monitoring/      →  outputs/reports/
                   →  dashboard/           →  Streamlit App
```

| Komponen | Teknologi |
|----------|-----------|
| Bahasa | Python 3.12 |
| Dashboard | Streamlit 1.45, Plotly 6.1 |
| Data Processing | Pandas 3.0, PyArrow 20.0 |
| Forecasting | Statsmodels (ETS, Holt-Winters, ARIMA) |
| Anomaly Detection | Scipy (Z-Score), Statsmodels (STL) |
| Storage | Parquet (columnar) |

---

## Fitur Dashboard (7 Halaman)

| Halaman | Deskripsi |
|---------|-----------|
| **Ringkasan KPI** | Scorecard eksekutif — revenue, orders, cancellation, shipping |
| **Tren Penjualan** | Analisis MoM growth, payment method breakdown, filter tahun interaktif |
| **Kategori Produk** | Pareto 80/20, BCG Matrix segmentation (Star/Cash Cow/Emerging/Declining) |
| **Analisis Wilayah** | Risk matrix 34 provinsi, peta konsentrasi, 424 kota |
| **Operasional** | Root cause cancellation (5 dimensi), courier performance |
| **Prediksi Pesanan** | Auto-select model terbaik (Naive/MA/ETS/Holt-Winters/ARIMA) |
| **Peringatan Dini** | Z-score anomaly detection, 5 metrik dipantau real-time |

---

## Pipeline Data (14 Langkah)

```
1.  Ingestion          — Load raw CSV (20.848 rows, semicolon-separated, UTF-8 BOM)
2.  Validation         — Schema check, null handling, type enforcement
3.  Staging            — Normalize columns, clean strings
4.  Transformation     — Feature engineering (54 derived columns)
5.  Dimension Build    — dim_date, dim_geography, dim_payment, dim_shipping, dim_status
6.  Fact Build         — fact_orders star schema
7.  KPI Analytics      — Revenue, cancellation, COD, shipping subsidy metrics
8.  Sales Analytics    — Monthly trend, MoM growth, payment analysis
9.  Geo Analytics      — Province/region/city performance, risk quadrant
10. Operations         — Cancellation breakdown (reason/initiator/payment/province)
11. Segmentation       — BCG Matrix category classification
12. Anomaly Detection  — Z-score + STL decomposition on 5 metrics
13. Early Warning      — Alert generation with severity classification
14. Decision Support   — Auto-generated strategic recommendations
```

---

## Cara Menjalankan Lokal

```bash
# Clone repository
git clone https://github.com/regiabdiputra/ecommerce-analytics-platform.git
cd ecommerce-analytics-platform

# Install dependencies
pip install -r requirements.txt

# Jalankan dashboard
streamlit run dashboard/app.py
```

Dashboard akan terbuka di `http://localhost:8501`.

> Catatan: Data mart sudah disertakan di repo (`data/marts/`). Pipeline tidak perlu dijalankan ulang untuk melihat dashboard.

---

## Struktur Project

```
├── dashboard/
│   ├── app.py                  # Landing page
│   ├── theme.py                # Design system (CSS, colors, components)
│   └── pages/
│       ├── 1_Overview.py
│       ├── 2_Sales_Trend.py
│       ├── 3_Category.py
│       ├── 4_Geographic.py
│       ├── 5_Operations.py
│       ├── 6_Forecasting.py
│       └── 7_Anomaly.py
├── src/
│   ├── ingestion/
│   ├── validation/
│   ├── transformation/
│   ├── analytics/
│   ├── forecasting/
│   └── monitoring/
├── data/
│   └── marts/                  # Star schema (fact + 6 dimensions)
├── outputs/
│   └── reports/                # 24 parquet marts + 5 JSON reports
├── run_pipeline.py             # Entry point pipeline
└── requirements.txt
```

---

## Dataset

- **Sumber**: Data transaksi e-commerce internal (dianonimkan)
- **Periode**: Desember 2023 — November 2025 (24 bulan)
- **Volume**: 20.848 baris, 19 kolom raw → 54 kolom setelah feature engineering
- **Format**: CSV semicolon-separated, UTF-8 BOM
- **Cakupan**: 34 provinsi, 424 kota, 38 kategori produk

---

## Dibuat oleh

**Regi Abdi Putra** — Analytics Engineer  
[LinkedIn](https://linkedin.com/in/regiabdiputra) · [GitHub](https://github.com/regiabdiputra)
