"""
Page 1: Ringkasan KPI — Executive Summary
"""
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go

st.set_page_config(page_title="Ringkasan KPI", layout="wide")

from theme import apply_theme, COLORS, chart_layout, page_header, section_header, callout, kpi_card

apply_theme()

REPORTS = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports"))

@st.cache_data
def load_kpi():
    with open(os.path.join(REPORTS, "kpi_summary.json"), encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_trend():
    return pd.read_parquet(os.path.join(REPORTS, "sales_monthly_trend.parquet"))

@st.cache_data
def load_rec():
    with open(os.path.join(REPORTS, "recommendations.json"), encoding="utf-8") as f:
        return json.load(f)

kpi   = load_kpi()
trend = load_trend()
rec   = load_rec()
ov    = kpi["overall_kpis"]

# Nilai-nilai kunci
total_orders = ov["total_orders"]["value"]
completed    = ov["completed_orders"]["value"]
cancelled    = ov["cancelled_orders"]["value"]
cancel_rate  = ov["cancellation_rate"]["value"]
revenue      = ov["total_revenue"]["value"]
aov          = ov["avg_order_value"]["value"]
cod_rate     = ov["cod_rate"]["value"]
cod_cancel   = ov["cod_cancellation_rate"]["value"]
free_ship    = ov["free_shipping_rate"]["value"]
avg_ship     = ov["avg_shipping_cost"]["value"]
java_conc    = ov["java_bali_concentration"]["value"]

page_header(
    "Ringkasan Eksekutif",
    "Gambaran menyeluruh kinerja bisnis e-commerce — Desember 2023 s/d November 2025"
)

# ── KPI baris 1 ───────────────────────────────────────────────────────────────
section_header("Kinerja Pesanan")
c1, c2, c3, c4, c5 = st.columns(5)
for col, lbl, val, sub, clr in [
    (c1, "Total Pesanan",      f"{total_orders:,}",             "Seluruh periode 24 bulan",         "blue"),
    (c2, "Pesanan Selesai",    f"{completed:,}",                f"Tingkat selesai {100-cancel_rate:.1f}%", "green"),
    (c3, "Tingkat Pembatalan", f"{cancel_rate:.1f}%",           f"{cancelled:,} pesanan gagal",      "red"),
    (c4, "Total Pendapatan",   f"Rp {revenue/1e9:.2f} Miliar",  "Dari pesanan yang berhasil",        "purple"),
    (c5, "Rata-rata per Transaksi", f"Rp {aov/1e3:.0f}.000",   "Per pesanan selesai",               "orange"),
]:
    col.markdown(kpi_card(lbl, val, sub, clr), unsafe_allow_html=True)

# ── Insight otomatis ──────────────────────────────────────────────────────────
last  = trend.iloc[-1]
prev  = trend.iloc[-2]
mom   = last["orders_mom_pct"] if pd.notna(last["orders_mom_pct"]) else 0
best  = trend.loc[trend["total_orders"].idxmax(), "year_month_str"]

i1, i2 = st.columns(2)
arah = "meningkat" if mom >= 0 else "menurun"
kind = "green" if mom >= 0 else "orange"
with i1:
    st.markdown(callout(
        f"Pesanan bulan terakhir <strong>{arah} {abs(mom):.1f}%</strong> dibandingkan bulan "
        f"sebelumnya. Bulan dengan pesanan tertinggi sepanjang periode adalah "
        f"<strong>{best}</strong> dengan {trend['total_orders'].max():,} pesanan.",
        kind=kind, label="Tren Terkini"
    ), unsafe_allow_html=True)
with i2:
    cod_kind = "red" if cod_cancel > 20 else "orange"
    st.markdown(callout(
        f"Sebanyak <strong>{cod_rate:.1f}%</strong> pesanan menggunakan COD (bayar di tempat). "
        f"Metode ini memiliki tingkat pembatalan <strong>{cod_cancel:.1f}%</strong> — "
        f"jauh lebih tinggi dibanding pembayaran digital.",
        kind=cod_kind, label="Risiko COD"
    ), unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── KPI baris 2 ───────────────────────────────────────────────────────────────
section_header("Pembayaran & Pengiriman")
c6, c7, c8, c9, c10 = st.columns(5)
for col, lbl, val, sub, clr in [
    (c6,  "Pesanan COD",         f"{cod_rate:.1f}%",     "Bayar di tempat",             "orange"),
    (c7,  "Pembatalan COD",      f"{cod_cancel:.1f}%",   "Tingkat batal khusus COD",    "red"),
    (c8,  "Ongkir Gratis",       f"{free_ship:.1f}%",    "Disubsidi platform",          "green"),
    (c9,  "Rata-rata Ongkir",    f"Rp {avg_ship/1e3:.0f}.000", "Per pesanan",            "blue"),
    (c10, "Konsentrasi Jawa-Bali", f"{java_conc:.1f}%",  "Dari total pesanan",          "orange"),
]:
    col.markdown(kpi_card(lbl, val, sub, clr), unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Grafik tren ───────────────────────────────────────────────────────────────
section_header("Tren Bulanan")

col_l, col_r = st.columns(2)

with col_l:
    st.markdown(f"""
    <div class="chart-card">
        <div class="chart-title">Jumlah Pesanan per Bulan</div>
        <div class="chart-caption">
            Batang biru = total pesanan &nbsp;|&nbsp; Garis hijau = pesanan selesai &nbsp;|&nbsp;
            Garis oranye putus = rata-rata bergerak 3 bulan (memperhalus fluktuasi musiman)
        </div>
    """, unsafe_allow_html=True)
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=trend["year_month_str"], y=trend["total_orders"],
        name="Total Pesanan", marker_color="#BBDEFB",
        marker_line_color=COLORS["primary"], marker_line_width=0.5,
    ))
    fig1.add_trace(go.Scatter(
        x=trend["year_month_str"], y=trend["completed_orders"],
        name="Selesai", mode="lines",
        line=dict(color=COLORS["success"], width=2),
    ))
    fig1.add_trace(go.Scatter(
        x=trend["year_month_str"], y=trend["orders_3m_rolling"],
        name="Rata-rata 3 Bulan", mode="lines",
        line=dict(color=COLORS["warning"], width=1.5, dash="dash"),
    ))
    fig1.update_layout(**chart_layout(height=300))
    fig1.update_layout(yaxis_title="Jumlah Pesanan")
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_r:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Pendapatan Bulanan (IDR)</div>
        <div class="chart-caption">
            Total pendapatan dari pesanan yang berhasil diselesaikan per bulan.
            Pola naik menunjukkan pertumbuhan bisnis yang sehat.
        </div>
    """, unsafe_allow_html=True)
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=trend["year_month_str"], y=trend["total_revenue"],
        name="Pendapatan",
        marker_color=COLORS["primary"], opacity=0.8,
    ))
    fig2.update_layout(**chart_layout(height=300))
    fig2.update_layout(yaxis_title="IDR", showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Grafik pembatalan
st.markdown("""
<div class="chart-card" style="margin-top:1rem;">
    <div class="chart-title">Tingkat Pembatalan per Bulan (%)</div>
    <div class="chart-caption">
        Hijau = bulan dengan pembatalan di bawah rata-rata (kondisi baik).
        Oranye/merah = bulan dengan pembatalan tinggi yang perlu diinvestigasi.
        Garis putus-putus = rata-rata keseluruhan.
    </div>
""", unsafe_allow_html=True)
avg_c = trend["cancellation_rate"].mean()
bar_colors = [
    COLORS["danger"]  if v > avg_c * 1.25 else
    COLORS["warning"] if v > avg_c else
    COLORS["success"]
    for v in trend["cancellation_rate"]
]
fig3 = go.Figure()
fig3.add_trace(go.Bar(
    x=trend["year_month_str"], y=trend["cancellation_rate"],
    marker_color=bar_colors, name="Tingkat Batal (%)",
))
fig3.add_hline(y=avg_c, line_dash="dash", line_color=COLORS["neutral"],
               annotation_text=f"Rata-rata: {avg_c:.1f}%",
               annotation_position="top left",
               annotation_font_color=COLORS["neutral"])
fig3.update_layout(**chart_layout(height=220))
fig3.update_layout(yaxis_title="Tingkat Pembatalan (%)", showlegend=False)
st.plotly_chart(fig3, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Rekomendasi ───────────────────────────────────────────────────────────────
section_header("Rekomendasi Strategis")
st.markdown(f"""
<p style="font-size:1rem;color:#37474F;margin-bottom:1.2rem;font-weight:500;">
    Sistem menghasilkan <strong style="color:#1A237E;">{rec['total_recommendations']} rekomendasi</strong> berdasarkan analisis data —
    <strong style="color:#B71C1C;">{rec['high_priority']} prioritas tinggi</strong>,
    <strong style="color:#7F3000;">{rec['medium_priority']} menengah</strong>,
    {rec['low_priority']} rendah.
</p>""", unsafe_allow_html=True)

prio_badge = {
    "high":   ("PRIORITAS TINGGI", "red"),
    "medium": ("MENENGAH",         "orange"),
    "low":    ("RENDAH",           "grey"),
}

for r in rec["recommendations"]:
    prio  = r.get("priority", "low")
    blabel, bkind = prio_badge.get(prio, ("RENDAH", "grey"))
    with st.expander(r.get("title", ""), expanded=(prio == "high")):
        from theme import badge
        st.markdown(badge(blabel, bkind), unsafe_allow_html=True)
        st.markdown(f"""
        <p style="font-size:1rem;color:#263238;margin:0.8rem 0 0.6rem;line-height:1.75;font-weight:400;">
            {r.get("recommendation", "")}
        </p>""", unsafe_allow_html=True)
        if r.get("evidence"):
            st.markdown(callout(r["evidence"], kind="blue", label="Data Pendukung"),
                        unsafe_allow_html=True)
        if r.get("expected_impact"):
            st.markdown(callout(r["expected_impact"], kind="green", label="Dampak yang Diharapkan"),
                        unsafe_allow_html=True)
