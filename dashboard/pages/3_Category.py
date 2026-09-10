"""
Page 3: Kategori Produk — Category performance & segmentation
"""
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Kategori Produk", layout="wide")

from theme import apply_theme, COLORS, chart_layout, page_header, section_header, callout, kpi_card, badge

apply_theme()

REPORTS = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports"))

@st.cache_data
def load_cat():
    return pd.read_parquet(os.path.join(REPORTS, "sales_category_performance.parquet"))

@st.cache_data
def load_seg():
    return pd.read_parquet(os.path.join(REPORTS, "seg_category_segments.parquet"))

cat = load_cat()
seg = load_seg()

page_header(
    "Performa Kategori Produk",
    "38 kategori peralatan rumah tangga plastik — mana yang paling laku dan paling menguntungkan?"
)

# ── Segmentasi summary ────────────────────────────────────────────────────────
section_header("Klasifikasi Strategis Kategori")

st.markdown(callout(
    "Setiap kategori diklasifikasikan berdasarkan dua dimensi: "
    "<strong>volume pesanan</strong> (tinggi atau rendah) dan "
    "<strong>pertumbuhan</strong> (tumbuh atau menyusut). "
    "Klasifikasi ini membantu menentukan di mana sebaiknya bisnis berfokus dan berinvestasi.",
    kind="blue", label="Cara Membaca Klasifikasi Ini"
), unsafe_allow_html=True)

seg_count = seg.groupby("segment")["category"].count().to_dict()
seg_defs = [
    ("Star Categories",     "green",  "Volume tinggi & tumbuh pesat. Prioritas utama — tingkatkan kapasitas."),
    ("Core Categories",     "blue",   "Volume tinggi, pertumbuhan melambat. Pertahankan — sumber pendapatan stabil."),
    ("Emerging Categories", "orange", "Volume kecil tapi tumbuh cepat. Investasikan — potensi masa depan."),
    ("Niche Categories",    "red",    "Volume kecil & menyusut. Evaluasi — pertimbangkan restrukturisasi."),
]

seg_labels = {
    "Star Categories":     "Star",
    "Core Categories":     "Cash Cow",
    "Emerging Categories": "Emerging",
    "Niche Categories":    "Declining",
}

s1, s2, s3, s4 = st.columns(4)
for col, (seg_name, clr, desc) in zip([s1, s2, s3, s4], seg_defs):
    count = seg_count.get(seg_name, 0)
    display = seg_labels[seg_name]
    col.markdown(f"""
    <div class="kpi-card {clr}" style="text-align:center;">
        <div class="kpi-label">{display}</div>
        <div class="kpi-value">{count}</div>
        <div class="kpi-sub">{desc}</div>
    </div>""", unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Filter & charts ───────────────────────────────────────────────────────────
section_header("Volume & Pendapatan per Kategori")

top_n = st.slider("Tampilkan berapa kategori teratas:", 5, 38, 15)
cat_top = cat.head(top_n)

st.markdown("""
<p style="font-size:0.83rem;color:#78909C;margin-bottom:0.8rem;">
    Warna batang mencerminkan tingkat pembatalan — biru tua menunjukkan pembatalan rendah (baik),
    merah menunjukkan pembatalan tinggi (perlu perhatian).
</p>""", unsafe_allow_html=True)

cl, cr = st.columns(2)

with cl:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Jumlah Pesanan per Kategori</div>
        <div class="chart-caption">
            Kategori diurutkan dari terbanyak ke tersedikit.
            Angka di ujung batang = total pesanan.
        </div>
    """, unsafe_allow_html=True)
    df_plot = cat_top.sort_values("total_orders")
    fig1 = go.Figure(go.Bar(
        x=df_plot["total_orders"], y=df_plot["category"],
        orientation="h",
        marker=dict(
            color=df_plot["cancellation_rate"],
            colorscale=[[0, COLORS["primary"]], [0.5, COLORS["warning"]], [1, COLORS["danger"]]],
            showscale=True,
            colorbar=dict(title="Batal %", thickness=12, len=0.6),
        ),
        text=df_plot["total_orders"],
        texttemplate="%{text:,}", textposition="outside",
        textfont=dict(size=9),
    ))
    fig1.update_layout(**chart_layout(height=max(350, top_n * 28)))
    fig1.update_layout(showlegend=False, xaxis_title="Jumlah Pesanan")
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with cr:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Porsi Pendapatan per Kategori (%)</div>
        <div class="chart-caption">
            Angka di ujung batang = porsi pendapatan dari total keseluruhan.
            Warna lebih gelap = nilai rata-rata per pesanan lebih tinggi.
        </div>
    """, unsafe_allow_html=True)
    df_plot2 = cat_top.sort_values("total_revenue")
    fig2 = go.Figure(go.Bar(
        x=df_plot2["total_revenue"], y=df_plot2["category"],
        orientation="h",
        marker=dict(
            color=df_plot2["avg_order_value"],
            colorscale=[[0, "#E3F2FD"], [1, COLORS["primary"]]],
            showscale=True,
            colorbar=dict(title="AOV (IDR)", thickness=12, len=0.6),
        ),
        text=df_plot2["revenue_share_pct"],
        texttemplate="%{text:.1f}%", textposition="outside",
        textfont=dict(size=9),
    ))
    fig2.update_layout(**chart_layout(height=max(350, top_n * 28)))
    fig2.update_layout(showlegend=False, xaxis_title="Pendapatan (IDR)")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Pareto ────────────────────────────────────────────────────────────────────
section_header("Analisis Pareto (Aturan 80/20)")

st.markdown(callout(
    "Dalam bisnis, umumnya <strong>20% produk menghasilkan 80% penjualan</strong>. "
    "Grafik ini menunjukkan berapa banyak kategori yang diperlukan untuk mencapai 80% total pesanan. "
    "Kategori di sebelah kiri garis merah adalah yang paling kritis untuk dipertahankan.",
    kind="blue", label="Apa itu Aturan 80/20?"
), unsafe_allow_html=True)

st.markdown("""
<div class="chart-card">
    <div class="chart-title">Distribusi Pesanan & Kumulatif per Kategori</div>
    <div class="chart-caption">
        Batang biru = porsi pesanan tiap kategori (%).
        Garis merah = akumulasi persentase dari kiri ke kanan.
        Garis putus-putus horizontal = batas 80%.
    </div>
""", unsafe_allow_html=True)
fig3 = go.Figure()
fig3.add_trace(go.Bar(
    x=cat["category"], y=cat["order_share_pct"],
    name="Porsi (%)", marker_color=COLORS["primary"], opacity=0.75,
))
fig3.add_trace(go.Scatter(
    x=cat["category"], y=cat["cumulative_order_share"],
    name="Kumulatif (%)", mode="lines+markers",
    line=dict(color=COLORS["danger"], width=2.5),
    marker=dict(size=4), yaxis="y2",
))
fig3.add_hline(y=80, line_dash="dash", line_color=COLORS["danger"],
               annotation_text="Batas 80%", yref="y2",
               annotation_font_color=COLORS["danger"])
layout3 = chart_layout(height=320)
layout3["yaxis"] = dict(title="Porsi (%)", gridcolor=COLORS["neutral_light"])
layout3["yaxis2"] = dict(title="Kumulatif (%)", overlaying="y", side="right",
                         range=[0, 105], showgrid=False)
layout3["xaxis"] = dict(tickangle=45, tickfont=dict(size=9))
fig3.update_layout(**layout3)
st.plotly_chart(fig3, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Scatter segmentasi ────────────────────────────────────────────────────────
section_header("Peta Posisi Kategori — Volume vs Pertumbuhan")

st.markdown(callout(
    "Grafik ini memetakan posisi setiap kategori berdasarkan dua dimensi. "
    "<strong>Sumbu horizontal</strong>: seberapa cepat pertumbuhan pesanan (semester 1 vs 2). "
    "<strong>Sumbu vertikal</strong>: seberapa besar volume pesanannya. "
    "Ukuran lingkaran mencerminkan volume — makin besar makin dominan. "
    "Posisi ideal: kanan atas (volume besar DAN tumbuh).",
    kind="blue", label="Cara Membaca Grafik Ini"
), unsafe_allow_html=True)

seg_label_map = {
    "Star Categories":     "Star",
    "Core Categories":     "Cash Cow",
    "Emerging Categories": "Emerging",
    "Niche Categories":    "Declining",
}
seg_plot = seg.copy()
seg_plot["Klasifikasi"] = seg_plot["segment"].map(seg_label_map)

seg_colors_plot = {
    "Star":      COLORS["success"],
    "Cash Cow":  COLORS["primary"],
    "Emerging":  COLORS["warning"],
    "Declining": COLORS["danger"],
}

st.markdown("""
<div class="chart-card">
    <div class="chart-title">Matriks Segmentasi Kategori</div>
    <div class="chart-caption">
        Garis abu-abu putus-putus = nilai median (titik tengah) untuk volume dan pertumbuhan.
    </div>
""", unsafe_allow_html=True)
fig4 = px.scatter(
    seg_plot, x="growth_pct", y="total_orders",
    color="Klasifikasi", text="category",
    size="total_orders", size_max=45,
    color_discrete_map=seg_colors_plot,
    labels={
        "growth_pct":   "Pertumbuhan (%) — Semester 1 vs Semester 2",
        "total_orders": "Total Pesanan",
        "Klasifikasi":  "Klasifikasi",
    },
    hover_data={"cancel_rate": True, "total_orders": True},
)
fig4.update_traces(textposition="top center", textfont=dict(size=9, color=COLORS["text_body"]))
fig4.add_vline(x=seg["growth_pct"].median(), line_dash="dash",
               line_color=COLORS["border"], annotation_text="Median pertumbuhan")
fig4.add_hline(y=seg["total_orders"].median(), line_dash="dash",
               line_color=COLORS["border"], annotation_text="Median volume")
layout4 = chart_layout(height=480)
layout4["plot_bgcolor"] = "#FAFBFC"
layout4["legend"] = dict(orientation="h", y=-0.15, font=dict(size=11))
fig4.update_layout(**layout4)
st.plotly_chart(fig4, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)
