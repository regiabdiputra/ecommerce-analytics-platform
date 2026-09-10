"""
Page 7: Peringatan Dini & Deteksi Anomali
"""
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

st.set_page_config(page_title="Peringatan Dini", layout="wide")

from theme import apply_theme, COLORS, chart_layout, page_header, section_header, callout, kpi_card, badge

apply_theme()

REPORTS = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports"))

@st.cache_data
def load_parquet(name):
    p = os.path.join(REPORTS, name)
    return pd.read_parquet(p) if os.path.exists(p) else pd.DataFrame()

@st.cache_data
def load_alerts():
    with open(os.path.join(REPORTS, "early_warning_alerts.json"), encoding="utf-8") as f:
        return json.load(f)

anom_vol      = load_parquet("anomaly_order_volume.parquet")
anom_cancel   = load_parquet("anomaly_cancellation_rate.parquet")
anom_payment  = load_parquet("anomaly_avg_payment.parquet")
anom_shipping = load_parquet("anomaly_shipping_cost.parquet")
anom_prov     = load_parquet("anomaly_province_cancellation.parquet")
alerts_data   = load_alerts()

alerts     = alerts_data.get("alerts", [])
n_critical = sum(1 for a in alerts if a.get("severity") == "Critical")
n_warning  = sum(1 for a in alerts if a.get("severity") == "Warning")
n_info     = sum(1 for a in alerts if a.get("severity") == "Info")

page_header(
    "Sistem Peringatan Dini & Deteksi Anomali",
    "Deteksi otomatis penyimpangan dari pola normal — sinyal peringatan sebelum masalah membesar"
)

# ── Penjelasan ────────────────────────────────────────────────────────────────
with st.expander("Bagaimana sistem ini bekerja?"):
    st.markdown(f"""
    Sistem memantau **5 metrik bisnis kritis** secara otomatis dan mendeteksi
    penyimpangan yang signifikan dari pola normal.

    | Metrik yang Dipantau | Yang Dideteksi |
    |---------------------|----------------|
    | Volume Pesanan | Penurunan atau lonjakan pesanan yang tidak wajar |
    | Tingkat Pembatalan | Lonjakan pembatalan di atas rata-rata historis |
    | Rata-rata Nilai Pembayaran | Perubahan signifikan pada nilai transaksi |
    | Biaya Pengiriman | Lonjakan biaya ongkir yang tidak normal |
    | Pembatalan per Provinsi | Provinsi dengan pembatalan jauh di atas rata-rata nasional |

    **Metode deteksi:** Z-Score (jarak dari rata-rata dalam satuan standar deviasi) dan
    STL Decomposition (pemisahan tren, musiman, dan residual).

    **Tingkat keparahan:**
    - **KRITIS** — Penyimpangan sangat besar, tindakan segera diperlukan
    - **PERINGATAN** — Perlu pemantauan lebih lanjut
    - **INFORMASI** — Catatan, tidak mendesak
    """)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Status panel ──────────────────────────────────────────────────────────────
section_header("Status Peringatan Aktif")

overall_status = "KRITIS" if n_critical > 0 else "WASPADA" if n_warning > 0 else "NORMAL"
overall_kind   = "red" if n_critical > 0 else "orange" if n_warning > 0 else "green"

st.markdown(callout(
    f"Status sistem saat ini: <strong>{overall_status}</strong>. "
    f"Terdapat {n_critical} sinyal kritis, {n_warning} peringatan, dan {n_info} informasi yang aktif.",
    kind=overall_kind, label="Status Keseluruhan Sistem"
), unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.markdown(kpi_card("Sinyal Kritis",   str(n_critical), "Tindakan segera diperlukan", "red"),     unsafe_allow_html=True)
c2.markdown(kpi_card("Peringatan",      str(n_warning),  "Perlu pemantauan",           "orange"),  unsafe_allow_html=True)
c3.markdown(kpi_card("Informasi",       str(n_info),     "Tidak mendesak",             "blue"),    unsafe_allow_html=True)
c4.markdown(kpi_card("Total Sinyal",    str(len(alerts)),"Semua tingkat keparahan",    "purple"),  unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Daftar peringatan ─────────────────────────────────────────────────────────
section_header("Daftar Peringatan")

if not alerts:
    st.markdown(callout(
        "Tidak ada peringatan aktif. Semua metrik yang dipantau berada dalam rentang normal.",
        kind="green", label="Sistem Normal"
    ), unsafe_allow_html=True)
else:
    sev_order = {"Critical": 0, "Warning": 1, "Info": 2}
    sev_badge = {"Critical": "red", "Warning": "orange", "Info": "blue"}
    sev_label = {"Critical": "KRITIS", "Warning": "PERINGATAN", "Info": "INFORMASI"}
    sev_kind  = {"Critical": "red", "Warning": "orange", "Info": "blue"}

    metric_labels = {
        "cancellation_rate":          "Tingkat Pembatalan Keseluruhan",
        "province_cancellation_rate": "Tingkat Pembatalan Provinsi",
        "order_volume":               "Volume Pesanan",
        "avg_payment":                "Rata-rata Nilai Pembayaran",
        "shipping_cost":              "Biaya Pengiriman",
    }

    sorted_alerts = sorted(alerts, key=lambda a: sev_order.get(a.get("severity", "Info"), 3))

    for a in sorted_alerts:
        sev    = a.get("severity", "Info")
        blabel = sev_label.get(sev, "INFORMASI")
        bkind  = sev_badge.get(sev, "blue")
        ckind  = sev_kind.get(sev, "blue")
        metric = metric_labels.get(a.get("metric", ""), a.get("metric", "").replace("_", " ").title())
        affected = a.get("affected", "")
        title  = f"{metric}" + (f" — {affected}" if affected else "")

        with st.expander(title, expanded=(sev == "Critical")):
            st.markdown(badge(blabel, bkind), unsafe_allow_html=True)

            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Nilai Saat Ini",      f"{a.get('current_value', 0):.2f}")
            mc2.metric("Nilai Normal (Baseline)", f"{a.get('baseline_value', 0):.2f}")
            dev = a.get("deviation_pct", 0)
            mc3.metric("Penyimpangan",        f"{dev:+.1f}%")

            desc = a.get("description", "").encode("utf-8", errors="replace").decode("utf-8")
            st.markdown(callout(desc, kind=ckind, label="Temuan"), unsafe_allow_html=True)
            if a.get("recommendation"):
                st.markdown(callout(
                    a["recommendation"], kind="blue", label="Rekomendasi Tindakan"
                ), unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Grafik monitoring ─────────────────────────────────────────────────────────
section_header("Grafik Monitoring Metrik")

st.markdown(f"""
<p style="font-size:0.85rem;color:{COLORS['text_muted']};margin-bottom:1rem;">
    Titik merah (x) pada grafik menandai periode di mana anomali terdeteksi.
    Grafik z-score di bawah menunjukkan seberapa jauh nilai dari rata-rata normal
    (garis putus-putus merah = batas deteksi pada 2 standar deviasi).
</p>""", unsafe_allow_html=True)


def plot_metric(df: pd.DataFrame, label: str, unit: str = ""):
    if df.empty:
        st.info("Data tidak tersedia untuk metrik ini.")
        return

    st.markdown(f"""
    <div class="chart-card">
        <div class="chart-title">{label}{' (' + unit + ')' if unit else ''}</div>
        <div class="chart-caption">
            Garis biru = nilai aktual. Garis abu-abu putus-putus = tren.
            Titik merah (x) = anomali terdeteksi oleh sistem.
        </div>
    """, unsafe_allow_html=True)
    fig = go.Figure()

    if "trend" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["period"], y=df["trend"], mode="lines",
            name="Tren", line=dict(color=COLORS["border"], width=1.5, dash="dot"),
        ))
    fig.add_trace(go.Scatter(
        x=df["period"], y=df["value"], mode="lines+markers",
        name="Nilai Aktual", line=dict(color=COLORS["primary"], width=2.5),
        marker=dict(size=5, color=COLORS["primary"]),
    ))
    if "anomaly_flag" in df.columns:
        pts = df[df["anomaly_flag"] == 1]
        if not pts.empty:
            fig.add_trace(go.Scatter(
                x=pts["period"], y=pts["value"], mode="markers",
                name="Anomali Terdeteksi",
                marker=dict(color=COLORS["danger"], size=13, symbol="x-thin",
                            line=dict(width=3, color=COLORS["danger"])),
            ))
    layout = chart_layout(height=240)
    layout["plot_bgcolor"] = "#FAFBFC"
    fig.update_layout(**layout)
    fig.update_layout(yaxis_title=label)
    st.plotly_chart(fig, use_container_width=True)

    if "z_score" in df.columns:
        z_colors = [
            COLORS["danger"] if abs(z) > 2 else
            COLORS["warning"] if abs(z) > 1.5 else
            COLORS["success"]
            for z in df["z_score"].fillna(0)
        ]
        fig_z = go.Figure(go.Bar(
            x=df["period"], y=df["z_score"].abs(),
            marker_color=z_colors, name="Z-Score",
        ))
        fig_z.add_hline(y=2, line_dash="dash", line_color=COLORS["danger"],
                        annotation_text="Batas deteksi (2 std. dev.)",
                        annotation_font_color=COLORS["danger"])
        layout_z = chart_layout(height=130)
        layout_z["margin"]["t"] = 5
        fig_z.update_layout(**layout_z)
        fig_z.update_layout(showlegend=False, yaxis_title="|Z|")
        st.plotly_chart(fig_z, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)


tab1, tab2, tab3, tab4 = st.tabs([
    "Volume Pesanan", "Tingkat Pembatalan",
    "Nilai Pembayaran", "Biaya Pengiriman"
])
with tab1: plot_metric(anom_vol,      "Volume Pesanan Bulanan", "pesanan")
with tab2: plot_metric(anom_cancel,   "Tingkat Pembatalan", "%")
with tab3: plot_metric(anom_payment,  "Rata-rata Nilai Pembayaran", "IDR")
with tab4: plot_metric(anom_shipping, "Rata-rata Biaya Ongkir", "IDR")

# ── Anomali provinsi ──────────────────────────────────────────────────────────
if not anom_prov.empty and "cancel_rate" in anom_prov.columns and "province_clean" in anom_prov.columns:
    st.markdown('<hr class="divider"/>', unsafe_allow_html=True)
    section_header("Anomali Pembatalan per Provinsi")

    st.markdown(callout(
        "Provinsi-provinsi berikut memiliki tingkat pembatalan yang secara statistik "
        "menyimpang signifikan dari rata-rata nasional. Investigasi lebih lanjut diperlukan "
        "untuk memahami faktor penyebabnya di masing-masing wilayah.",
        kind="orange", label="Interpretasi"
    ), unsafe_allow_html=True)

    flag_col = "anomaly_flag" if "anomaly_flag" in anom_prov.columns else None
    flagged  = anom_prov[anom_prov[flag_col] == 1] if flag_col else anom_prov

    if not flagged.empty:
        st.markdown("""
        <div class="chart-card">
            <div class="chart-title">Provinsi dengan Tingkat Pembatalan Anomali (%)</div>
        """, unsafe_allow_html=True)
        fig_prov = go.Figure(go.Bar(
            x=flagged.sort_values("cancel_rate")["cancel_rate"],
            y=flagged.sort_values("cancel_rate")["province_clean"],
            orientation="h",
            marker_color=COLORS["danger"], opacity=0.8,
            text=flagged.sort_values("cancel_rate")["cancel_rate"].round(1),
            texttemplate="%{text:.1f}%", textposition="outside",
        ))
        fig_prov.update_layout(**chart_layout(height=max(280, len(flagged) * 35)))
        fig_prov.update_layout(showlegend=False, xaxis_title="Tingkat Pembatalan (%)")
        st.plotly_chart(fig_prov, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(callout(
            "Tidak ada provinsi yang menunjukkan anomali pembatalan yang signifikan saat ini.",
            kind="green", label="Status Normal"
        ), unsafe_allow_html=True)
