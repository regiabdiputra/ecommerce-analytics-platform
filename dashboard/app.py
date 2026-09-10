"""
Landing page — Analytics Platform
"""
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import json

st.set_page_config(
    page_title="Platform Analitik Penjualan",
    page_icon="assets/favicon.ico" if os.path.exists("assets/favicon.ico") else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

from theme import apply_theme, COLORS

apply_theme()

REPORTS = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "outputs", "reports"))

@st.cache_data
def load_kpi():
    with open(os.path.join(REPORTS, "kpi_summary.json"), encoding="utf-8") as f:
        return json.load(f)

kpi = load_kpi()
ov  = kpi["overall_kpis"]

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#1B4F8A 0%,#1565C0 100%);
            padding:2rem 2.2rem;border-radius:12px;margin-bottom:1.2rem;
            box-shadow:0 3px 10px rgba(27,79,138,0.22);">
    <div style="color:#FFFFFF !important;font-size:1.9rem;font-weight:700;
                margin:0 0 0.3rem 0;letter-spacing:-0.02em;font-family:Inter,sans-serif;">
        Platform Analitik Penjualan &amp; Operasional
    </div>
    <div style="color:#FFFFFF !important;font-size:1.05rem;font-weight:400;
                margin-bottom:0.4rem;font-family:Inter,sans-serif;">
        Dashboard intelijen bisnis berbasis data untuk e-commerce Indonesia
        &nbsp;&mdash;&nbsp; Desember 2023 hingga November 2025
    </div>
    <div style="color:#FFFFFF !important;font-size:0.95rem;font-weight:400;
                opacity:0.85;font-family:Inter,sans-serif;">
        20.848 pesanan &nbsp;|&nbsp; 34 provinsi &nbsp;|&nbsp;
        38 kategori produk &nbsp;|&nbsp; 24 bulan data
    </div>
</div>
""", unsafe_allow_html=True)

# ── Snapshot KPI ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Ringkasan Bisnis</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
cards = [
    (c1, "Total Pesanan",       f"{ov['total_orders']['value']:,}",
         "Seluruh periode data", "blue"),
    (c2, "Pesanan Selesai",     f"{ov['completed_orders']['value']:,}",
         f"Tingkat keberhasilan {100-ov['cancellation_rate']['value']:.1f}%", "green"),
    (c3, "Tingkat Pembatalan",  f"{ov['cancellation_rate']['value']:.1f}%",
         f"{ov['cancelled_orders']['value']:,} pesanan dibatalkan", "red"),
    (c4, "Total Pendapatan",    f"Rp {ov['total_revenue']['value']/1e9:.1f} M",
         "Dari pesanan yang selesai", "purple"),
    (c5, "Rata-rata Nilai Pesanan", f"Rp {ov['avg_order_value']['value']/1e3:.0f} rb",
         "Per transaksi berhasil", "orange"),
]
for col, label, val, sub, color in cards:
    col.markdown(f"""
    <div class="kpi-card {'' if color=='blue' else color}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{val}</div>
        <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Navigasi halaman ──────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Halaman Dashboard</div>', unsafe_allow_html=True)

pages = [
    ("Ringkasan KPI",
     "Scorecard bisnis lengkap — gambaran menyeluruh kinerja penjualan, pendapatan, dan pembatalan pesanan dalam satu tampilan.",
     "Gunakan halaman ini sebagai titik awal sebelum menyelami detail lebih dalam."),
    ("Tren Penjualan",
     "Analisis pergerakan pesanan dan pendapatan dari bulan ke bulan. Apakah bisnis sedang tumbuh atau melambat?",
     "Cocok untuk memantau perubahan kinerja dan mengidentifikasi bulan terbaik/terburuk."),
    ("Kategori Produk",
     "Produk mana yang paling laku? Mana yang pertumbuhannya paling pesat? Klasifikasi 38 kategori secara strategis.",
     "Membantu keputusan investasi stok dan pengembangan produk."),
    ("Analisis Wilayah",
     "Pemetaan distribusi pesanan di 34 provinsi dan 424 kota. Mana pasar utama dan mana yang berisiko?",
     "Berguna untuk strategi ekspansi dan manajemen risiko regional."),
    ("Operasional",
     "Analisis mendalam penyebab pembatalan dan kinerja pengiriman. Apa yang perlu diperbaiki?",
     "Fokus pada pengurangan biaya tersembunyi akibat pembatalan dan inefisiensi logistik."),
    ("Prediksi Pesanan",
     "Estimasi volume pesanan untuk bulan-bulan mendatang menggunakan model statistik terpilih secara otomatis.",
     "Membantu perencanaan stok, SDM, dan kapasitas logistik."),
    ("Peringatan Dini",
     "Deteksi otomatis penyimpangan dari pola normal — sinyal peringatan sebelum masalah menjadi besar.",
     "Pantau metrik kritis dan tanggapi anomali lebih cepat."),
]

cols_r1 = st.columns(4)
cols_r2 = st.columns(3)

for i, (title, desc, use) in enumerate(pages):
    col = cols_r1[i] if i < 4 else cols_r2[i - 4]
    num = str(i + 1)
    with col:
        st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #E0E7EF;border-radius:10px;
                    padding:1.2rem;height:200px;
                    box-shadow:0 1px 4px rgba(0,0,0,0.05);
                    border-top:3px solid {COLORS['primary']};">
            <div style="font-size:0.7rem;font-weight:700;color:{COLORS['text_muted']};
                        text-transform:uppercase;letter-spacing:0.07em;margin-bottom:0.4rem;">
                Halaman {num}
            </div>
            <div style="font-size:0.95rem;font-weight:700;color:{COLORS['text_primary']};
                        margin-bottom:0.5rem;">{title}</div>
            <div style="font-size:0.78rem;color:{COLORS['text_body']};line-height:1.5;
                        margin-bottom:0.4rem;">{desc}</div>
            <div style="font-size:0.74rem;color:{COLORS['text_muted']};font-style:italic;">{use}</div>
        </div>""", unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Panduan penggunaan ────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Panduan Penggunaan</div>', unsafe_allow_html=True)

g1, g2, g3 = st.columns(3)
guides = [
    ("Navigasi", "Pilih halaman dari menu di sidebar kiri. Setiap halaman memiliki fokus analisis yang berbeda."),
    ("Membaca Grafik",
     "Arahkan kursor ke grafik untuk melihat angka detail. Klik item di legenda untuk menyembunyikan/menampilkan data."),
    ("Kode Warna",
     "Biru = informasi umum. Hijau = kondisi baik. Oranye = perlu perhatian. Merah = kondisi berisiko."),
]
for col, (title, text) in zip([g1, g2, g3], guides):
    col.markdown(f"""
    <div class="callout callout-blue">
        <span class="callout-label">{title}</span>
        {text}
    </div>""", unsafe_allow_html=True)

st.markdown(f"""
<p style="font-size:0.75rem;color:{COLORS['text_muted']};margin-top:2rem;text-align:center;">
    Platform Analitik Penjualan &amp; Operasional &nbsp;|&nbsp;
    Dibuat dengan Python, Streamlit, Plotly &nbsp;|&nbsp;
    Data per: {kpi['generated_at'][:10]}
</p>""", unsafe_allow_html=True)
