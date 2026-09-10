"""
Page 6: Prediksi Pesanan — Order volume forecasting
"""
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Prediksi Pesanan", layout="wide")

from theme import apply_theme, COLORS, chart_layout, page_header, section_header, callout, kpi_card

apply_theme()

REPORTS     = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports"))
PROJECT_ROOT= os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

@st.cache_data
def load_trend():
    return pd.read_parquet(os.path.join(REPORTS, "sales_monthly_trend.parquet"))

@st.cache_data
def load_fact():
    return pd.read_parquet(os.path.join(PROJECT_ROOT, "data", "marts", "fact_orders.parquet"))

@st.cache_data(show_spinner="Menjalankan model prediksi, harap tunggu...")
def run_forecast(horizon: int):
    from src.forecasting.forecaster import run_forecasting
    return run_forecasting(load_fact(), horizon=horizon)

trend = load_trend()

page_header(
    "Prediksi Volume Pesanan",
    "Estimasi jumlah pesanan untuk bulan-bulan mendatang menggunakan model statistik terpilih secara otomatis"
)

# ── Penjelasan ────────────────────────────────────────────────────────────────
with st.expander("Bagaimana cara kerja sistem prediksi ini?"):
    st.markdown(f"""
    Sistem mencoba **5 model prediksi** secara bersamaan, kemudian memilih yang paling akurat
    berdasarkan pengujian terhadap data historis.

    | Model | Logika Sederhana |
    |-------|-----------------|
    | Naive | "Bulan depan sama dengan bulan ini" |
    | Moving Average | Rata-rata dari 3 bulan terakhir |
    | Exponential Smoothing | Rata-rata berbobot — data terbaru lebih diprioritaskan |
    | Holt-Winters | Memperhitungkan tren naik/turun dan pola musiman |
    | ARIMA | Model matematika yang mendeteksi pola tersembunyi dalam data |

    Model dipilih berdasarkan **sMAPE** — rata-rata persentase selisih antara prediksi dan data nyata.
    Semakin kecil nilainya, semakin akurat modelnya.

    > **Catatan penting:** Prediksi ini didasarkan pada pola historis.
    > Kejadian tak terduga seperti promo besar, bencana, atau perubahan kebijakan platform
    > tidak dapat diprediksi oleh model statistik.
    """)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Kontrol ───────────────────────────────────────────────────────────────────
section_header("Pengaturan Prediksi")

col_h, col_run = st.columns([3, 1])
with col_h:
    horizon = st.slider(
        "Jumlah bulan yang ingin diprediksi:",
        min_value=1, max_value=6, value=3,
        help="Prediksi lebih dari 3 bulan ke depan memiliki tingkat ketidakpastian yang lebih tinggi."
    )
    if horizon > 3:
        st.markdown(callout(
            "Prediksi lebih dari 3 bulan ke depan memiliki rentang ketidakpastian yang lebih lebar. "
            "Gunakan sebagai perkiraan kasar, bukan angka pasti.",
            kind="orange", label="Perhatian"
        ), unsafe_allow_html=True)
with col_run:
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("Jalankan Prediksi", type="primary", use_container_width=True)

if "forecast_result" not in st.session_state:
    st.session_state["forecast_result"] = None
if "forecast_horizon" not in st.session_state:
    st.session_state["forecast_horizon"] = horizon

if run_btn:
    st.session_state["forecast_result"] = run_forecast(horizon)
    st.session_state["forecast_horizon"] = horizon

# ── Riwayat historis ──────────────────────────────────────────────────────────
section_header("Riwayat Volume Pesanan Bulanan")

st.markdown("""
<div class="chart-card">
    <div class="chart-title">Data Historis — Dasar Perhitungan Prediksi</div>
    <div class="chart-caption">
        Batang biru = jumlah pesanan aktual per bulan.
        Garis oranye putus-putus = rata-rata bergerak 3 bulan.
    </div>
""", unsafe_allow_html=True)
fig_hist = go.Figure()
fig_hist.add_trace(go.Bar(
    x=trend["year_month_str"], y=trend["total_orders"],
    name="Pesanan Aktual", marker_color="#BBDEFB",
    marker_line_color=COLORS["primary"], marker_line_width=0.4,
))
fig_hist.add_trace(go.Scatter(
    x=trend["year_month_str"], y=trend["orders_3m_rolling"],
    mode="lines", name="Rata-rata 3 Bulan",
    line=dict(color=COLORS["warning"], width=2, dash="dash"),
))
fig_hist.update_layout(**chart_layout(height=260))
fig_hist.update_layout(yaxis_title="Jumlah Pesanan")
st.plotly_chart(fig_hist, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── Hasil prediksi ────────────────────────────────────────────────────────────
result = st.session_state.get("forecast_result")

if result is None:
    st.markdown(callout(
        "Klik tombol <strong>Jalankan Prediksi</strong> di atas untuk melihat hasil estimasi "
        "volume pesanan bulan-bulan mendatang.",
        kind="blue", label="Cara Menggunakan"
    ), unsafe_allow_html=True)

elif "error" in result:
    st.markdown(callout(str(result["error"]), kind="red", label="Error"), unsafe_allow_html=True)

else:
    h           = st.session_state["forecast_horizon"]
    fc_df       = result.get("forecast", pd.DataFrame())
    best_model  = result.get("best_model", "unknown")
    last_period = trend["year_month_str"].iloc[-1]

    model_labels = {
        "holt_winters":  "Holt-Winters",
        "arima":         "ARIMA",
        "moving_avg_3":  "Moving Average (3 Bulan)",
        "exp_smoothing": "Exponential Smoothing",
        "naive":         "Naive",
    }
    model_display = model_labels.get(best_model, best_model)

    st.markdown('<hr class="divider"/>', unsafe_allow_html=True)
    section_header("Hasil Prediksi")

    st.markdown(callout(
        f"Model yang dipilih secara otomatis: <strong>{model_display}</strong>. "
        f"Model ini memiliki akurasi terbaik berdasarkan pengujian terhadap 6 bulan data terakhir.",
        kind="green", label="Model Terpilih"
    ), unsafe_allow_html=True)

    # Kartu angka prediksi
    if not fc_df.empty:
        fc_cols = st.columns(len(fc_df))
        for i, (_, row) in enumerate(fc_df.iterrows()):
            fc_cols[i].markdown(f"""
            <div class="kpi-card" style="text-align:center;background:linear-gradient(135deg,#1B4F8A,#1565C0);">
                <div class="kpi-label" style="color:rgba(255,255,255,0.7);">{row['year_month_str']}</div>
                <div class="kpi-value" style="color:#FFFFFF;font-size:2rem;">{row['forecast_orders']:,}</div>
                <div class="kpi-sub" style="color:rgba(255,255,255,0.65);">
                    Kisaran: {row['ci_lower']:,} &ndash; {row['ci_upper']:,}
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Grafik prediksi
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Visualisasi Prediksi — 12 Bulan Terakhir + Estimasi</div>
        <div class="chart-caption">
            Garis biru = data historis aktual.
            Garis merah putus-putus = hasil prediksi.
            Area merah transparan = rentang ketidakpastian 95%
            (nilai aktual kemungkinan besar jatuh di dalam area ini).
        </div>
    """, unsafe_allow_html=True)
    fig_fc = go.Figure()
    hist_tail = trend.tail(12)
    fig_fc.add_trace(go.Scatter(
        x=hist_tail["year_month_str"], y=hist_tail["total_orders"],
        mode="lines+markers", name="Data Historis",
        line=dict(color=COLORS["primary"], width=2.5),
        marker=dict(size=6, color=COLORS["primary"]),
    ))
    if not fc_df.empty:
        fp = fc_df["year_month_str"].tolist()
        fv = fc_df["forecast_orders"].tolist()
        fl = fc_df["ci_lower"].tolist()
        fu = fc_df["ci_upper"].tolist()

        fig_fc.add_trace(go.Scatter(
            x=fp, y=fv, mode="lines+markers",
            name=f"Prediksi ({model_display})",
            line=dict(color=COLORS["danger"], width=2.5, dash="dot"),
            marker=dict(size=9, symbol="diamond", color=COLORS["danger"]),
        ))
        fig_fc.add_trace(go.Scatter(
            x=fp + fp[::-1], y=fu + fl[::-1],
            fill="toself", fillcolor="rgba(198,40,40,0.1)",
            line=dict(color="rgba(0,0,0,0)"),
            name="Rentang Ketidakpastian (95%)",
        ))

    # add_vline doesn't support string/categorical x — use shape instead
    all_x = hist_tail["year_month_str"].tolist() + (fp if not fc_df.empty else [])
    if last_period in all_x:
        x_idx = all_x.index(last_period)
        fig_fc.add_shape(type="line",
            x0=x_idx + 0.5, x1=x_idx + 0.5, y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(dash="dash", color=COLORS["border"], width=1.5),
        )
        fig_fc.add_annotation(
            x=x_idx + 0.5, y=1, xref="x", yref="paper",
            text="Awal prediksi", showarrow=False,
            font=dict(size=12, color=COLORS["text_muted"]),
            xanchor="left", yanchor="top",
        )
    layout_fc = chart_layout(height=360)
    layout_fc["plot_bgcolor"] = "#FAFBFC"
    fig_fc.update_layout(**layout_fc)
    fig_fc.update_layout(yaxis_title="Jumlah Pesanan")
    st.plotly_chart(fig_fc, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Perbandingan model
    st.markdown('<hr class="divider"/>', unsafe_allow_html=True)
    section_header("Perbandingan Akurasi Model")

    st.markdown(f"""
    <p style="font-size:0.85rem;color:{COLORS['text_muted']};margin-bottom:1rem;">
        sMAPE (Symmetric Mean Absolute Percentage Error) mengukur rata-rata persentase kesalahan prediksi.
        Semakin kecil angkanya, semakin akurat modelnya. Nilai di bawah 10% dianggap baik.
    </p>""", unsafe_allow_html=True)

    cv = result.get("all_model_metrics", {})
    if cv:
        cv_df = pd.DataFrame(cv).T.reset_index().rename(columns={"index": "Model"})
        cv_df["Model"] = cv_df["Model"].map(model_labels).fillna(cv_df["Model"])
        cv_df = cv_df.sort_values("sMAPE").reset_index(drop=True)

        cm1, cm2 = st.columns([2, 1])
        with cm1:
            st.markdown("""
            <div class="chart-card">
                <div class="chart-title">sMAPE per Model (lebih kecil lebih baik)</div>
            """, unsafe_allow_html=True)
            bar_colors_cv = [COLORS["success"]] + [COLORS["primary"]] * (len(cv_df) - 1)
            fig_cv = go.Figure(go.Bar(
                x=cv_df["sMAPE"], y=cv_df["Model"],
                orientation="h", marker_color=bar_colors_cv,
                text=cv_df["sMAPE"].round(1),
                texttemplate="%{text:.1f}%", textposition="outside",
            ))
            fig_cv.update_layout(**chart_layout(height=280))
            fig_cv.update_layout(showlegend=False, xaxis_title="sMAPE (%)")
            st.plotly_chart(fig_cv, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with cm2:
            cv_df["Status"] = ["Terpilih"] + [""] * (len(cv_df) - 1)
            st.dataframe(
                cv_df[["Model", "MAE", "RMSE", "sMAPE", "Status"]].style.format(
                    {"MAE": "{:.1f}", "RMSE": "{:.1f}", "sMAPE": "{:.2f}%"}
                ),
                use_container_width=True, hide_index=True,
            )

    if result.get("disclaimer"):
        st.markdown(f"""
        <p style="font-size:0.75rem;color:{COLORS['text_muted']};margin-top:1rem;
                  padding:0.8rem;background:#F5F7FA;border-radius:6px;
                  border:1px solid {COLORS['border']};">
            Catatan: {result['disclaimer']}
        </p>""", unsafe_allow_html=True)
