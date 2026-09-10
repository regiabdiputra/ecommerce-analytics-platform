"""
Page 4: Analisis Wilayah — Geographic performance
"""
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Analisis Wilayah", layout="wide")

from theme import apply_theme, COLORS, chart_layout, page_header, section_header, callout, kpi_card

apply_theme()

REPORTS = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports"))

@st.cache_data
def load_prov():   return pd.read_parquet(os.path.join(REPORTS, "geo_province.parquet"))
@st.cache_data
def load_region(): return pd.read_parquet(os.path.join(REPORTS, "geo_region_group.parquet"))
@st.cache_data
def load_city():   return pd.read_parquet(os.path.join(REPORTS, "geo_city.parquet"))

prov   = load_prov()
region = load_region()
city   = load_city()

page_header(
    "Analisis Wilayah & Geografi",
    "Distribusi pesanan di 34 provinsi dan 424 kota — pasar utama, risiko regional, dan peluang ekspansi"
)

# ── Region summary ────────────────────────────────────────────────────────────
section_header("Distribusi per Kawasan")

region_sorted = region.sort_values("total_orders", ascending=False)
rcols = st.columns(len(region_sorted))
border_colors = [COLORS["primary"], COLORS["success"], COLORS["warning"],
                 COLORS["danger"], "#00695C", "#4527A0"]

for i, (_, row) in enumerate(region_sorted.iterrows()):
    cancel_color = COLORS["danger"] if row["cancellation_rate"] > 15 else \
                   COLORS["warning"] if row["cancellation_rate"] > 10 else COLORS["success"]
    rcols[i].markdown(f"""
    <div class="kpi-card" style="border-left-color:{border_colors[i % len(border_colors)]};text-align:center;">
        <div class="kpi-label">{row['region_group']}</div>
        <div class="kpi-value">{row['total_orders']:,}</div>
        <div class="kpi-sub">{row['order_share_pct']:.1f}% dari total</div>
        <div class="kpi-sub" style="color:{cancel_color};font-weight:600;">
            Batal: {row['cancellation_rate']:.1f}%
        </div>
    </div>""", unsafe_allow_html=True)

# ── Insight konsentrasi ───────────────────────────────────────────────────────
top_prov = prov.iloc[0]
java_share = region[region["region_group"] == "Jawa-Bali"]["order_share_pct"].sum()

i1, i2 = st.columns(2)
with i1:
    st.markdown(callout(
        f"Kawasan Jawa, Bali, dan Banten menyumbang sekitar <strong>{java_share:.0f}%</strong> "
        f"dari seluruh pesanan. Ketergantungan tinggi pada satu kawasan menciptakan risiko "
        f"konsentrasi — gangguan di area ini berdampak besar pada bisnis secara keseluruhan.",
        kind="orange", label="Risiko Konsentrasi Wilayah"
    ), unsafe_allow_html=True)
with i2:
    st.markdown(callout(
        f"Provinsi <strong>{top_prov['province_clean']}</strong> adalah pasar terbesar dengan "
        f"<strong>{top_prov['total_orders']:,} pesanan</strong> "
        f"({top_prov['order_share_pct']:.1f}% dari total) dan tingkat penyelesaian "
        f"<strong>{top_prov['completion_rate']:.1f}%</strong>.",
        kind="blue", label="Pasar Utama"
    ), unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Province charts ───────────────────────────────────────────────────────────
section_header("Performa 20 Provinsi Teratas")

st.markdown("""
<p style="font-size:0.83rem;color:#78909C;margin-bottom:1rem;">
    Warna batang mencerminkan tingkat pembatalan — biru tua berarti rendah (baik),
    merah berarti tinggi (perlu perhatian).
    Angka di ujung batang menunjukkan porsi dari total pesanan nasional.
</p>""", unsafe_allow_html=True)

cl, cr = st.columns(2)

with cl:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Volume Pesanan per Provinsi (Top 20)</div>
        <div class="chart-caption">Diurutkan dari terbanyak ke tersedikit.</div>
    """, unsafe_allow_html=True)
    top20 = prov.head(20).sort_values("total_orders")
    fig1 = go.Figure(go.Bar(
        x=top20["total_orders"], y=top20["province_clean"],
        orientation="h",
        marker=dict(
            color=top20["cancellation_rate"],
            colorscale=[[0, COLORS["primary"]], [0.5, COLORS["warning"]], [1, COLORS["danger"]]],
            showscale=True,
            colorbar=dict(title="Batal %", thickness=12, len=0.6),
        ),
        text=top20["order_share_pct"],
        texttemplate="%{text:.1f}%", textposition="outside",
        textfont=dict(size=9),
    ))
    fig1.update_layout(**chart_layout(height=520))
    fig1.update_layout(showlegend=False, xaxis_title="Jumlah Pesanan")
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with cr:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Pendapatan vs Tingkat Pembatalan per Provinsi</div>
        <div class="chart-caption">
            Ukuran lingkaran = volume pesanan. Posisi ideal: kiri atas
            (pendapatan tinggi, pembatalan rendah).
        </div>
    """, unsafe_allow_html=True)
    fig2 = px.scatter(
        prov, x="cancellation_rate", y="total_revenue",
        size="total_orders", color="region_group",
        hover_name="province_clean",
        color_discrete_sequence=[COLORS["chart1"], COLORS["chart2"], COLORS["chart3"],
                                  COLORS["chart4"], COLORS["chart5"], COLORS["chart6"]],
        labels={
            "cancellation_rate": "Tingkat Pembatalan (%)",
            "total_revenue":     "Total Pendapatan (IDR)",
            "region_group":      "Kawasan",
        },
        size_max=40,
    )
    layout2 = chart_layout(height=520)
    layout2["plot_bgcolor"] = "#FAFBFC"
    layout2["legend"] = dict(orientation="h", y=-0.15, font=dict(size=10))
    fig2.update_layout(**layout2)
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Risk matrix ───────────────────────────────────────────────────────────────
section_header("Matriks Risiko Provinsi")

st.markdown(callout(
    "<strong>Cara membaca matriks ini:</strong> Setiap provinsi diposisikan berdasarkan dua dimensi — "
    "seberapa besar porsi pesanannya (sumbu vertikal) dan seberapa tinggi risiko pembatalannya (sumbu horizontal). "
    "<br><br>"
    "<strong>Kiri Atas</strong> = Pasar utama, risiko rendah — pertahankan. &nbsp;|&nbsp; "
    "<strong>Kanan Atas</strong> = Volume besar, berisiko tinggi — prioritas perbaikan. <br>"
    "<strong>Kiri Bawah</strong> = Volume kecil, aman — potensi ekspansi. &nbsp;|&nbsp; "
    "<strong>Kanan Bawah</strong> = Volume kecil, berisiko — evaluasi ulang.",
    kind="blue", label="Panduan Membaca Matriks"
), unsafe_allow_html=True)

quadrant_colors = {
    "Core Market":             COLORS["success"],
    "High Volume / High Risk": COLORS["danger"],
    "Low Volume / Low Risk":   COLORS["primary"],
    "Low Volume / High Risk":  COLORS["warning"],
}

st.markdown("""
<div class="chart-card">
    <div class="chart-title">Peta Risiko — Volume vs Tingkat Pembatalan</div>
    <div class="chart-caption">
        Ukuran lingkaran = volume pesanan. Arahkan kursor untuk melihat detail tiap provinsi.
        Garis abu-abu putus-putus = nilai median.
    </div>
""", unsafe_allow_html=True)
fig3 = px.scatter(
    prov, x="cancellation_rate", y="order_share_pct",
    color="quadrant", hover_name="province_clean",
    size="total_orders", size_max=40,
    color_discrete_map=quadrant_colors,
    labels={
        "cancellation_rate": "Tingkat Pembatalan (%)",
        "order_share_pct":   "Porsi Pesanan (%)",
        "quadrant":          "Kuadran",
    },
    hover_data={"total_orders": True, "total_revenue": True},
)
fig3.add_vline(x=prov["cancellation_rate"].median(), line_dash="dash",
               line_color=COLORS["border"], annotation_text="Median pembatalan")
fig3.add_hline(y=prov["order_share_pct"].median(), line_dash="dash",
               line_color=COLORS["border"], annotation_text="Median volume")
layout3 = chart_layout(height=420)
layout3["plot_bgcolor"] = "#FAFBFC"
layout3["legend"] = dict(orientation="h", y=-0.18, font=dict(size=11))
fig3.update_layout(**layout3)
st.plotly_chart(fig3, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Top kota ──────────────────────────────────────────────────────────────────
section_header("30 Kota dengan Volume Pesanan Tertinggi")

st.markdown("""
<div class="chart-card">
    <div class="chart-title">Volume Pesanan per Kota/Kabupaten</div>
    <div class="chart-caption">
        Warna mencerminkan tingkat pembatalan di kota tersebut.
        Arahkan kursor untuk melihat provinsi asal kota.
    </div>
""", unsafe_allow_html=True)
fig4 = go.Figure(go.Bar(
    x=city.sort_values("total_orders")["total_orders"],
    y=city.sort_values("total_orders")["city_clean"],
    orientation="h",
    marker=dict(
        color=city.sort_values("total_orders")["cancellation_rate"],
        colorscale=[[0, COLORS["primary"]], [0.5, COLORS["warning"]], [1, COLORS["danger"]]],
        showscale=True,
        colorbar=dict(title="Batal %", thickness=12),
    ),
    customdata=city.sort_values("total_orders")[["province_clean", "city_type"]],
    hovertemplate="<b>%{y}</b><br>Pesanan: %{x:,}<br>Provinsi: %{customdata[0]}<br>Tipe: %{customdata[1]}<extra></extra>",
))
fig4.update_layout(**chart_layout(height=680))
fig4.update_layout(showlegend=False, xaxis_title="Jumlah Pesanan")
st.plotly_chart(fig4, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

with st.expander("Lihat Tabel Lengkap Semua Provinsi"):
    st.dataframe(
        prov[["province_clean","region_group","total_orders","completed_orders",
              "cancellation_rate","total_revenue","cod_rate","order_share_pct",
              "revenue_share_pct","growth_pct","quadrant"]].rename(columns={
            "province_clean":"Provinsi","region_group":"Kawasan",
            "total_orders":"Total Pesanan","completed_orders":"Selesai",
            "cancellation_rate":"Tingkat Batal %","total_revenue":"Pendapatan (IDR)",
            "cod_rate":"COD %","order_share_pct":"Porsi %",
            "revenue_share_pct":"Porsi Pendapatan %","growth_pct":"Pertumbuhan %",
            "quadrant":"Kuadran Risiko",
        }),
        use_container_width=True, hide_index=True,
    )
