"""
Page 2: Tren Penjualan — Monthly sales trend analysis
"""
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Tren Penjualan", layout="wide")

from theme import apply_theme, COLORS, CHART_SERIES, chart_layout, page_header, section_header, callout

apply_theme()

REPORTS = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports"))

@st.cache_data
def load_trend():
    return pd.read_parquet(os.path.join(REPORTS, "sales_monthly_trend.parquet"))

@st.cache_data
def load_payment():
    return pd.read_parquet(os.path.join(REPORTS, "sales_payment_analysis.parquet"))

trend = load_trend()
pay   = load_payment()

page_header(
    "Tren Penjualan Bulanan",
    "Pergerakan jumlah pesanan dan pendapatan dari bulan ke bulan — apakah bisnis sedang tumbuh?"
)

# ── Filter tahun ─────────────────────────────────────────────────────────────
years = sorted(trend["year"].unique())

# Inisialisasi session state untuk tiap tahun
for y in years:
    key = f"yr_{y}"
    if key not in st.session_state:
        st.session_state[key] = True

# Render toggle buttons dalam satu baris
btn_cols = st.columns([2] + [1] * len(years) + [8])
btn_cols[0].markdown(
    '<div style="padding:0.45rem 0;font-size:0.88rem;font-weight:700;'
    'color:#1B4F8A;text-transform:uppercase;letter-spacing:0.06em;">'
    'Filter Tahun</div>',
    unsafe_allow_html=True
)
for i, y in enumerate(years):
    key = f"yr_{y}"
    active = st.session_state[key]
    label = f"{'✓  ' if active else ''}{y}"
    btn_style = (
        "background:#1B4F8A;color:#FFFFFF;border:2px solid #1B4F8A;"
        if active else
        "background:#FFFFFF;color:#1B4F8A;border:2px solid #1B4F8A;"
    )
    if btn_cols[i + 1].button(
        label,
        key=f"btn_{y}",
        help=f"{'Sembunyikan' if active else 'Tampilkan'} data tahun {y}",
        use_container_width=True,
    ):
        st.session_state[key] = not active
        st.rerun()

sel = [y for y in years if st.session_state.get(f"yr_{y}", True)]
if not sel:
    st.warning("Pilih minimal satu tahun untuk menampilkan data.", icon="⚠️")
    st.stop()

df = trend[trend["year"].isin(sel)].copy()

# ── KPI ringkasan ─────────────────────────────────────────────────────────────
section_header("Ringkasan Periode Terpilih")

best_row   = df.loc[df["total_orders"].idxmax()]
worst_row  = df.loc[df["total_orders"].idxmin()]
last_row   = df.iloc[-1]
mom_orders = last_row["orders_mom_pct"] if pd.notna(last_row["orders_mom_pct"]) else 0
mom_rev    = last_row["revenue_mom_pct"] if pd.notna(last_row["revenue_mom_pct"]) else 0
avg_orders = df["total_orders"].mean()

c1, c2, c3, c4 = st.columns(4)
from theme import kpi_card
c1.markdown(kpi_card("Bulan Terbaik",      best_row["year_month_str"],
                     f"{best_row['total_orders']:,} pesanan", "green"), unsafe_allow_html=True)
c2.markdown(kpi_card("Bulan Terlemah",     worst_row["year_month_str"],
                     f"{worst_row['total_orders']:,} pesanan", "red"), unsafe_allow_html=True)
c3.markdown(kpi_card("Rata-rata Pesanan/Bulan", f"{avg_orders:,.0f}",
                     f"Dari {len(df)} bulan", "blue"), unsafe_allow_html=True)
mom_color = "green" if mom_orders >= 0 else "orange"
c4.markdown(kpi_card("Pertumbuhan Bulan Terakhir", f"{mom_orders:+.1f}%",
                     f"Pendapatan {mom_rev:+.1f}%", mom_color), unsafe_allow_html=True)

# ── Insight ───────────────────────────────────────────────────────────────────
i1, i2 = st.columns(2)
arah = "meningkat" if mom_orders >= 0 else "menurun"
months_above = (df["total_orders"] > avg_orders).sum()
with i1:
    st.markdown(callout(
        f"Jumlah pesanan {arah} <strong>{abs(mom_orders):.1f}%</strong> di bulan terakhir "
        f"({last_row['year_month_str']}). Pendapatan turut {arah} "
        f"<strong>{abs(mom_rev):.1f}%</strong>.",
        kind="green" if mom_orders >= 0 else "orange",
        label="Kondisi Terkini"
    ), unsafe_allow_html=True)
with i2:
    st.markdown(callout(
        f"Dari <strong>{len(df)} bulan</strong> yang ditampilkan, "
        f"<strong>{months_above} bulan</strong> mencatatkan pesanan di atas rata-rata "
        f"({avg_orders:,.0f} pesanan/bulan). "
        f"Puncak tertinggi terjadi pada <strong>{best_row['year_month_str']}</strong>.",
        kind="blue", label="Konsistensi Kinerja"
    ), unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Grafik utama ──────────────────────────────────────────────────────────────
section_header("Pesanan & Pendapatan per Bulan")

st.markdown("""
<div class="chart-card">
    <div class="chart-title">Volume Pesanan vs Pendapatan</div>
    <div class="chart-caption">
        Batang biru (skala kanan) = pendapatan bulanan dalam IDR.
        Garis oranye (skala kiri) = jumlah pesanan.
        Garis merah putus-putus = rata-rata bergerak 3 bulan untuk memperhalus tren.
    </div>
""", unsafe_allow_html=True)

fig = go.Figure()
fig.add_trace(go.Bar(
    x=df["year_month_str"], y=df["total_revenue"],
    name="Pendapatan (IDR)", marker_color="#BBDEFB",
    marker_line_color=COLORS["primary"], marker_line_width=0.3,
    yaxis="y2", opacity=0.85,
))
fig.add_trace(go.Scatter(
    x=df["year_month_str"], y=df["total_orders"],
    mode="lines+markers", name="Jumlah Pesanan",
    line=dict(color=COLORS["warning"], width=2.5),
    marker=dict(size=5, color=COLORS["warning"]),
))
fig.add_trace(go.Scatter(
    x=df["year_month_str"], y=df["orders_3m_rolling"],
    mode="lines", name="Rata-rata 3 Bulan",
    line=dict(color=COLORS["danger"], width=1.5, dash="dash"),
))
layout = chart_layout(height=360)
layout["yaxis"] = dict(title="Jumlah Pesanan", gridcolor=COLORS["neutral_light"],
                       tickfont=dict(size=13))
layout["yaxis2"] = dict(title="Pendapatan (IDR)", overlaying="y", side="right",
                        tickfont=dict(size=13), showgrid=False)
layout["hovermode"] = "x unified"
fig.update_layout(**layout)
st.plotly_chart(fig, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── Pertumbuhan MoM ───────────────────────────────────────────────────────────
section_header("Pertumbuhan Bulan ke Bulan")

st.markdown("""
<p style="font-size:1rem;color:#37474F;margin-bottom:1rem;font-weight:500;">
    Pertumbuhan positif (hijau) berarti pesanan/pendapatan naik dibanding bulan sebelumnya.
    Negatif (merah) berarti turun. Volatilitas tinggi menunjukkan ketidakstabilan permintaan.
</p>""", unsafe_allow_html=True)

cl, cr = st.columns(2)

with cl:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Pertumbuhan Jumlah Pesanan (%)</div>
        <div class="chart-caption">Dibandingkan bulan sebelumnya. Hijau = tumbuh, Merah = turun.</div>
    """, unsafe_allow_html=True)
    colors_o = [COLORS["success"] if v >= 0 else COLORS["danger"]
                for v in df["orders_mom_pct"].fillna(0)]
    fig2 = go.Figure(go.Bar(
        x=df["year_month_str"], y=df["orders_mom_pct"],
        marker_color=colors_o,
        text=df["orders_mom_pct"].round(1),
        texttemplate="%{text:+.1f}%", textposition="outside",
        textfont=dict(size=12),
    ))
    fig2.add_hline(y=0, line_color=COLORS["neutral"], line_width=1.5)
    fig2.update_layout(**chart_layout(height=280))
    fig2.update_layout(showlegend=False, yaxis_title="% Perubahan")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with cr:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Pertumbuhan Pendapatan (%)</div>
        <div class="chart-caption">Dibandingkan bulan sebelumnya. Perhatikan apakah pola sejalan dengan pesanan.</div>
    """, unsafe_allow_html=True)
    colors_r = [COLORS["success"] if v >= 0 else COLORS["danger"]
                for v in df["revenue_mom_pct"].fillna(0)]
    fig3 = go.Figure(go.Bar(
        x=df["year_month_str"], y=df["revenue_mom_pct"],
        marker_color=colors_r,
        text=df["revenue_mom_pct"].round(1),
        texttemplate="%{text:+.1f}%", textposition="outside",
        textfont=dict(size=12),
    ))
    fig3.add_hline(y=0, line_color=COLORS["neutral"], line_width=1.5)
    fig3.update_layout(**chart_layout(height=280))
    fig3.update_layout(showlegend=False, yaxis_title="% Perubahan")
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Metode pembayaran ─────────────────────────────────────────────────────────
section_header("Analisis Metode Pembayaran")

st.markdown(callout(
    "Metode pembayaran berpengaruh langsung pada tingkat pembatalan. "
    "COD (bayar di tempat) secara konsisten memiliki risiko pembatalan lebih tinggi "
    "karena pembeli dapat menolak paket saat kurir tiba.",
    kind="blue", label="Mengapa Ini Penting"
), unsafe_allow_html=True)

pa, pb = st.columns(2)

with pa:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Porsi Pesanan per Metode Pembayaran</div>
        <div class="chart-caption">Distribusi volume pesanan berdasarkan cara pembeli membayar.</div>
    """, unsafe_allow_html=True)
    fig4 = go.Figure(go.Pie(
        values=pay["total_orders"],
        labels=pay["metode_pembayaran"],
        hole=0.45,
        marker=dict(colors=CHART_SERIES),
        textinfo="label+percent",
        textfont=dict(size=13),
    ))
    fig4.update_layout(**chart_layout(height=300))
    fig4.update_layout(showlegend=False)
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with pb:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Tingkat Pembatalan per Metode Pembayaran (%)</div>
        <div class="chart-caption">
            Semakin panjang batangnya, semakin berisiko metode tersebut.
            Warna merah = risiko tinggi.
        </div>
    """, unsafe_allow_html=True)
    fig5 = go.Figure(go.Bar(
        x=pay.sort_values("cancellation_rate")["cancellation_rate"],
        y=pay.sort_values("cancellation_rate")["metode_pembayaran"],
        orientation="h",
        marker_color=[
            COLORS["danger"] if v > 20 else
            COLORS["warning"] if v > 12 else
            COLORS["success"]
            for v in pay.sort_values("cancellation_rate")["cancellation_rate"]
        ],
        text=pay.sort_values("cancellation_rate")["cancellation_rate"].round(1),
        texttemplate="%{text:.1f}%", textposition="outside",
    ))
    fig5.update_layout(**chart_layout(height=300))
    fig5.update_layout(showlegend=False, xaxis_title="Tingkat Pembatalan (%)")
    st.plotly_chart(fig5, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Tabel ─────────────────────────────────────────────────────────────────────
with st.expander("Lihat Data Lengkap per Bulan"):
    cols = ["year_month_str","total_orders","completed_orders","cancelled_orders",
            "total_revenue","cancellation_rate","orders_mom_pct","revenue_mom_pct"]
    st.dataframe(
        df[cols].rename(columns={
            "year_month_str":"Bulan","total_orders":"Total Pesanan",
            "completed_orders":"Selesai","cancelled_orders":"Dibatalkan",
            "total_revenue":"Pendapatan (IDR)","cancellation_rate":"Tingkat Batal %",
            "orders_mom_pct":"Tumbuh Pesanan %","revenue_mom_pct":"Tumbuh Pendapatan %",
        }),
        use_container_width=True, hide_index=True,
    )
