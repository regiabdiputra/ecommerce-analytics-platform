"""
Page 5: Operasional — Cancellation & shipping analysis
"""
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json

st.set_page_config(page_title="Operasional", layout="wide")

from theme import apply_theme, COLORS, chart_layout, page_header, section_header, callout, kpi_card

apply_theme()

REPORTS = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports"))

@st.cache_data
def load_json(name):
    with open(os.path.join(REPORTS, name), encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_df(name):
    return pd.read_parquet(os.path.join(REPORTS, name))

ops       = load_json("ops_summary.json")
c_reason  = load_df("ops_cancellation_by_reason.parquet")
c_init    = load_df("ops_cancellation_by_initiator.parquet")
c_pay     = load_df("ops_cancellation_by_payment.parquet")
c_prov    = load_df("ops_cancellation_by_province.parquet")
c_monthly = load_df("ops_cancellation_monthly_trend.parquet")
s_courier = load_df("ops_shipping_by_courier.parquet")
s_tier    = load_df("ops_shipping_by_tier.parquet")
s_monthly = load_df("ops_shipping_monthly_trend.parquet")

page_header(
    "Analisis Operasional",
    "Penyebab pembatalan pesanan, kinerja pengiriman, dan efisiensi operasional bisnis"
)

# ── KPI baris ─────────────────────────────────────────────────────────────────
section_header("Ringkasan Operasional")

c1, c2, c3, c4, c5, c6 = st.columns(6)
for col, lbl, val, sub, clr in [
    (c1, "Total Pesanan",      f"{ops['total_orders']:,}",
         "Semua status",                          "blue"),
    (c2, "Tingkat Selesai",    f"{ops['completion_rate_pct']:.1f}%",
         f"{ops['completed']:,} pesanan berhasil", "green"),
    (c3, "Tingkat Pembatalan", f"{ops['cancellation_rate_pct']:.1f}%",
         f"{ops['cancelled']:,} pesanan gagal",    "red"),
    (c4, "Ongkir Gratis",      f"{ops['free_shipping_pct']:.1f}%",
         "Disubsidi platform",                    "teal"),
    (c5, "Rata-rata Subsidi",  f"{ops['avg_platform_subsidy_pct']:.1f}%",
         "Per pesanan bersubsidi",                "orange"),
    (c6, "Tingkat Retur",      f"{ops['return_rate_pct']:.2f}%",
         "Barang dikembalikan",                   "purple"),
]:
    col.markdown(kpi_card(lbl, val, sub, clr), unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Analisis pembatalan ───────────────────────────────────────────────────────
section_header("Analisis Pembatalan Pesanan")

st.markdown(callout(
    "Setiap pesanan yang dibatalkan berarti pendapatan yang hilang dan biaya operasional yang terbuang. "
    "Memahami <strong>penyebab, pelaku, dan pola waktu</strong> pembatalan adalah kunci untuk menguranginya. "
    "Gunakan tab di bawah untuk menelusuri data dari berbagai sudut pandang.",
    kind="blue", label="Mengapa Analisis Pembatalan Penting"
), unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Tren Bulanan", "Penyebab", "Pihak yang Membatalkan",
    "Per Metode Pembayaran", "Per Provinsi"
])

with tab1:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Tren Tingkat Pembatalan Bulanan</div>
        <div class="chart-caption">
            Batang merah = jumlah pesanan yang dibatalkan per bulan (skala kanan).
            Garis merah gelap = tingkat pembatalan dalam persen (skala kiri).
            Garis oranye putus-putus = rata-rata bergerak 3 bulan.
        </div>
    """, unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=c_monthly["year_month_str"], y=c_monthly["cancelled"],
        name="Jumlah Dibatalkan",
        marker_color="#FFCDD2", marker_line_color=COLORS["danger"], marker_line_width=0.5,
        yaxis="y2",
    ))
    fig.add_trace(go.Scatter(
        x=c_monthly["year_month_str"], y=c_monthly["cancel_rate"],
        name="Tingkat Batal (%)", mode="lines+markers",
        line=dict(color=COLORS["danger"], width=2.5),
        marker=dict(size=5),
    ))
    if "cancel_rate_3m_avg" in c_monthly.columns:
        fig.add_trace(go.Scatter(
            x=c_monthly["year_month_str"], y=c_monthly["cancel_rate_3m_avg"],
            name="Rata-rata 3 Bulan", mode="lines",
            line=dict(color=COLORS["warning"], width=1.5, dash="dash"),
        ))
    layout = chart_layout(height=320)
    layout["yaxis"]  = dict(title="Tingkat Batal (%)", gridcolor=COLORS["neutral_light"])
    layout["yaxis2"] = dict(title="Jumlah Dibatalkan", overlaying="y", side="right", showgrid=False)
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    top_reason = c_reason.iloc[0]
    st.markdown(callout(
        f"Penyebab terbesar pembatalan adalah <strong>\"{top_reason['cancellation_reason_clean']}\"</strong> "
        f"yang menyumbang <strong>{top_reason['pct']:.1f}%</strong> dari total pembatalan "
        f"({top_reason['count']:,} kasus). Tangani penyebab ini untuk dampak terbesar.",
        kind="red", label="Penyebab Utama"
    ), unsafe_allow_html=True)

    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Distribusi Penyebab Pembatalan</div>
        <div class="chart-caption">Warna lebih gelap = porsi lebih besar dari total pembatalan.</div>
    """, unsafe_allow_html=True)
    fig2 = go.Figure(go.Bar(
        x=c_reason.sort_values("count")["count"],
        y=c_reason.sort_values("count")["cancellation_reason_clean"],
        orientation="h",
        marker_color=COLORS["danger"], opacity=0.8,
        text=c_reason.sort_values("count")["pct"],
        texttemplate="%{text:.1f}%", textposition="outside",
    ))
    fig2.update_layout(**chart_layout(height=350))
    fig2.update_layout(showlegend=False, xaxis_title="Jumlah Kejadian")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab3:
    top_init = c_init.iloc[0]
    st.markdown(callout(
        f"Sebagian besar pembatalan ({top_init['pct']:.1f}%) diprakarsai oleh "
        f"<strong>{top_init['cancellation_initiator']}</strong>. "
        f"Memahami pihak yang memulai pembatalan membantu menentukan strategi mitigasi yang tepat.",
        kind="blue", label="Temuan Kunci"
    ), unsafe_allow_html=True)

    pa, pb = st.columns(2)
    with pa:
        st.markdown("""
        <div class="chart-card">
            <div class="chart-title">Komposisi Pihak yang Membatalkan</div>
        """, unsafe_allow_html=True)
        fig3 = go.Figure(go.Pie(
            values=c_init["count"], labels=c_init["cancellation_initiator"],
            hole=0.45,
            marker=dict(colors=[COLORS["danger"], COLORS["warning"], COLORS["primary"]]),
            textinfo="label+percent", textfont=dict(size=11),
        ))
        fig3.update_layout(**chart_layout(height=300))
        fig3.update_layout(showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with pb:
        st.dataframe(
            c_init.rename(columns={
                "cancellation_initiator": "Pihak",
                "count": "Jumlah", "pct": "Porsi (%)"
            }),
            use_container_width=True, hide_index=True,
        )

with tab4:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Tingkat Pembatalan per Metode Pembayaran (%)</div>
        <div class="chart-caption">
            Metode pembayaran dengan batang lebih panjang = lebih berisiko.
            Warna merah = tingkat pembatalan tinggi.
        </div>
    """, unsafe_allow_html=True)
    sorted_pay = c_pay.sort_values("cancel_rate")
    fig4 = go.Figure(go.Bar(
        x=sorted_pay["cancel_rate"],
        y=sorted_pay["metode_pembayaran"],
        orientation="h",
        marker_color=[
            COLORS["danger"] if v > 20 else
            COLORS["warning"] if v > 12 else
            COLORS["success"]
            for v in sorted_pay["cancel_rate"]
        ],
        text=sorted_pay["cancel_rate"].round(1),
        texttemplate="%{text:.1f}%", textposition="outside",
    ))
    fig4.update_layout(**chart_layout(height=360))
    fig4.update_layout(showlegend=False, xaxis_title="Tingkat Pembatalan (%)")
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab5:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Tingkat Pembatalan 20 Provinsi Tertinggi (%)</div>
        <div class="chart-caption">
            Provinsi dengan tingkat pembatalan jauh di atas rata-rata nasional
            memerlukan investigasi dan tindakan spesifik.
        </div>
    """, unsafe_allow_html=True)
    top20p = c_prov.sort_values("cancel_rate", ascending=False).head(20).sort_values("cancel_rate")
    avg_national = c_prov["cancel_rate"].mean()
    fig5 = go.Figure(go.Bar(
        x=top20p["cancel_rate"], y=top20p["province_clean"],
        orientation="h",
        marker_color=[
            COLORS["danger"] if v > avg_national * 1.3 else
            COLORS["warning"] if v > avg_national else
            COLORS["success"]
            for v in top20p["cancel_rate"]
        ],
        text=top20p["cancel_rate"].round(1),
        texttemplate="%{text:.1f}%", textposition="outside",
    ))
    fig5.add_vline(x=avg_national, line_dash="dash", line_color=COLORS["neutral"],
                   annotation_text=f"Rata-rata: {avg_national:.1f}%")
    fig5.update_layout(**chart_layout(height=520))
    fig5.update_layout(showlegend=False, xaxis_title="Tingkat Pembatalan (%)")
    st.plotly_chart(fig5, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Analisis pengiriman ───────────────────────────────────────────────────────
section_header("Analisis Pengiriman")

st.markdown(callout(
    "Biaya pengiriman adalah komponen operasional yang signifikan. "
    "Pilihan kurir dan kelas layanan pengiriman berpengaruh langsung pada kepuasan pelanggan "
    "dan efisiensi biaya. Analisis ini membantu mengidentifikasi opsi pengiriman yang paling optimal.",
    kind="blue", label="Konteks Analisis"
), unsafe_allow_html=True)

ts1, ts2, ts3 = st.tabs(["Tren Biaya Bulanan", "Per Kurir", "Per Kelas Layanan"])

with ts1:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Tren Total Biaya Pengiriman Bulanan (IDR)</div>
        <div class="chart-caption">
            Garis biru = total biaya ongkir. Garis oranye putus-putus = total subsidi dari platform.
            Selisih antara keduanya adalah biaya yang ditanggung pembeli.
        </div>
    """, unsafe_allow_html=True)
    fig_s1 = go.Figure()
    fig_s1.add_trace(go.Scatter(
        x=s_monthly["year_month_str"], y=s_monthly["total_shipping_cost"],
        mode="lines+markers", name="Total Biaya Ongkir",
        line=dict(color=COLORS["primary"], width=2.5),
        marker=dict(size=5),
    ))
    if "total_subsidy" in s_monthly.columns:
        fig_s1.add_trace(go.Scatter(
            x=s_monthly["year_month_str"], y=s_monthly["total_subsidy"],
            mode="lines", name="Subsidi Platform",
            line=dict(color=COLORS["warning"], width=1.5, dash="dash"),
        ))
    fig_s1.update_layout(**chart_layout(height=300))
    fig_s1.update_layout(yaxis_title="IDR")
    st.plotly_chart(fig_s1, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with ts2:
    # Deteksi dan tampilkan peringatan untuk kurir anomali
    other_courier = s_courier[s_courier["shipping_courier"] == "other"]
    if not other_courier.empty and other_courier.iloc[0]["cancel_rate"] > 50:
        st.markdown(callout(
            f"Kurir berlabel <strong>'other'</strong> memiliki tingkat pembatalan "
            f"<strong>{other_courier.iloc[0]['cancel_rate']:.1f}%</strong> dari "
            f"{other_courier.iloc[0]['total_orders']:,} pesanan — angka ini tidak wajar. "
            "Kemungkinan besar ini adalah pesanan yang belum memiliki kurir terdaftar di sistem, "
            "bukan kegagalan kurir sesungguhnya. Data ini perlu ditelusuri lebih lanjut di sisi operasional.",
            kind="orange", label="Catatan Data: Kurir 'Other'"
        ), unsafe_allow_html=True)

    sa, sb = st.columns(2)
    with sa:
        st.markdown("""
        <div class="chart-card">
            <div class="chart-title">Volume Pesanan per Kurir</div>
        """, unsafe_allow_html=True)
        fig_s2a = go.Figure(go.Bar(
            x=s_courier.sort_values("total_orders")["total_orders"],
            y=s_courier.sort_values("total_orders")["shipping_courier"],
            orientation="h", marker_color=COLORS["primary"], opacity=0.8,
        ))
        fig_s2a.update_layout(**chart_layout(height=320))
        fig_s2a.update_layout(showlegend=False, xaxis_title="Jumlah Pesanan")
        st.plotly_chart(fig_s2a, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with sb:
        st.markdown("""
        <div class="chart-card">
            <div class="chart-title">Rata-rata Biaya Ongkir per Kurir (IDR)</div>
            <div class="chart-caption">Warna mencerminkan tingkat pembatalan kurir tersebut.</div>
        """, unsafe_allow_html=True)
        fig_s2b = go.Figure(go.Bar(
            x=s_courier.sort_values("avg_shipping_cost")["avg_shipping_cost"],
            y=s_courier.sort_values("avg_shipping_cost")["shipping_courier"],
            orientation="h",
            marker=dict(
                color=s_courier.sort_values("avg_shipping_cost")["cancel_rate"],
                colorscale=[[0, COLORS["success"]], [0.5, COLORS["warning"]], [1, COLORS["danger"]]],
                showscale=True,
                colorbar=dict(title="Batal %", thickness=12),
            ),
        ))
        fig_s2b.update_layout(**chart_layout(height=320))
        fig_s2b.update_layout(showlegend=False, xaxis_title="Rata-rata Ongkir (IDR)")
        st.plotly_chart(fig_s2b, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

with ts3:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Volume Pesanan per Kelas Layanan Pengiriman</div>
        <div class="chart-caption">
            REG = Reguler, EXP = Ekspres, dst.
            Kelas layanan mencerminkan kecepatan pengiriman yang dipilih pembeli.
        </div>
    """, unsafe_allow_html=True)
    fig_s3 = go.Figure(go.Bar(
        x=s_tier.sort_values("total_orders", ascending=False)["shipping_tier"],
        y=s_tier.sort_values("total_orders", ascending=False)["total_orders"],
        marker_color=COLORS["primary"], opacity=0.8,
        text=s_tier.sort_values("total_orders", ascending=False)["total_orders"],
        texttemplate="%{text:,}", textposition="outside",
    ))
    fig_s3.update_layout(**chart_layout(height=300))
    fig_s3.update_layout(showlegend=False, yaxis_title="Jumlah Pesanan")
    st.plotly_chart(fig_s3, use_container_width=True)
    st.dataframe(s_tier.rename(columns={
        "shipping_tier": "Kelas Layanan", "total_orders": "Jumlah Pesanan",
    }), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
