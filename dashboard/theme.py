"""
Shared theme module — Professional design system for the analytics dashboard.
Import this in every page: from theme import apply_theme, COLORS, chart_layout
"""
import streamlit as st

# ── Color palette ─────────────────────────────────────────────────────────────
COLORS = {
    "primary":      "#1B4F8A",   # deep navy blue — main brand color
    "primary_light":"#2E6DB4",   # medium blue for hover/accent
    "accent":       "#2196F3",   # bright blue for highlights
    "success":      "#2E7D32",   # dark green
    "success_light":"#E8F5E9",
    "warning":      "#E65100",   # deep orange
    "warning_light":"#FFF3E0",
    "danger":       "#C62828",   # dark red
    "danger_light": "#FFEBEE",
    "neutral":      "#37474F",   # blue-grey text
    "neutral_light":"#ECEFF1",   # light grey background
    "border":       "#CFD8DC",   # grey border
    "white":        "#FFFFFF",
    "bg":           "#F5F7FA",   # page background
    "card_bg":      "#FFFFFF",
    "text_primary": "#1A237E",   # very dark blue for headings
    "text_body":    "#37474F",   # dark grey for body text
    "text_muted":   "#78909C",   # muted grey for captions
    # chart series
    "chart1":       "#1B4F8A",
    "chart2":       "#2196F3",
    "chart3":       "#26A69A",
    "chart4":       "#7E57C2",
    "chart5":       "#EF5350",
    "chart6":       "#FFA726",
}

CHART_SERIES = [
    COLORS["chart1"], COLORS["chart2"], COLORS["chart3"],
    COLORS["chart4"], COLORS["chart5"], COLORS["chart6"],
]

# ── Plotly layout defaults ────────────────────────────────────────────────────
def chart_layout(height=340, margin_bottom=40, title=None):
    layout = dict(
        height=height,
        margin=dict(l=4, r=4, t=36 if title else 10, b=margin_bottom),
        plot_bgcolor=COLORS["white"],
        paper_bgcolor=COLORS["white"],
        font=dict(family="Inter, Segoe UI, Arial, sans-serif",
                  color=COLORS["text_body"], size=14),
        legend=dict(
            orientation="h", y=-0.18,
            font=dict(size=13),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            showgrid=False,
            linecolor=COLORS["border"],
            tickfont=dict(size=13, color=COLORS["text_muted"]),
        ),
        yaxis=dict(
            gridcolor=COLORS["neutral_light"],
            linecolor="rgba(0,0,0,0)",
            tickfont=dict(size=13, color=COLORS["text_muted"]),
        ),
        hoverlabel=dict(
            bgcolor=COLORS["white"],
            bordercolor=COLORS["border"],
            font=dict(size=12, color=COLORS["text_body"]),
        ),
    )
    if title:
        layout["title"] = dict(
            text=title,
            font=dict(size=14, color=COLORS["text_primary"], family="Inter, Segoe UI, Arial"),
            x=0, xanchor="left", pad=dict(l=4),
        )
    return layout


# ── Global CSS ────────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Reset & base */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important;
}
.main .block-container {
    padding: 1.5rem 2rem 2rem 2rem;
    max-width: 1400px;
    background-color: #F5F7FA;
}
.stApp {
    background-color: #F5F7FA;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #1B4F8A;
    border-right: none;
}
[data-testid="stSidebar"] * {
    color: #E3F2FD !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
    border-radius: 6px;
    margin: 2px 8px;
    padding: 6px 10px;
}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
    background-color: rgba(255,255,255,0.12) !important;
}
[data-testid="stSidebar"] [aria-selected="true"] {
    background-color: rgba(255,255,255,0.18) !important;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Page header */
.page-header {
    background: linear-gradient(135deg, #1B4F8A 0%, #1565C0 100%);
    padding: 1.8rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.2rem;
    box-shadow: 0 3px 10px rgba(27,79,138,0.22);
}
.page-header h1 {
    color: #FFFFFF !important;
    font-size: 1.9rem;
    font-weight: 700;
    margin: 0 0 0.2rem 0;
    letter-spacing: -0.02em;
}
.page-header-sub,
.page-header div,
.page-header span,
.page-header p,
.page-header p *,
.page-header div *,
div.page-header > div,
div.page-header p,
div.page-header div {
    color: #FFFFFF !important;
    font-size: 1.08rem !important;
    font-weight: 400 !important;
    margin: 0 !important;
}

/* KPI cards */
.kpi-row {
    display: flex;
    gap: 1rem;
    margin: 1rem 0;
}
.kpi-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 1.5rem 1.8rem;
    flex: 1;
    border: 1px solid #BBDEFB;
    box-shadow: 0 3px 8px rgba(27,79,138,0.10);
    border-left: 6px solid #1B4F8A;
    min-height: 110px;
}
.kpi-card.green  { border-left-color: #2E7D32; border-color: #C8E6C9; }
.kpi-card.red    { border-left-color: #C62828; border-color: #FFCDD2; }
.kpi-card.orange { border-left-color: #E65100; border-color: #FFE0B2; }
.kpi-card.purple { border-left-color: #4527A0; border-color: #D1C4E9; }
.kpi-card.teal   { border-left-color: #00695C; border-color: #B2DFDB; }

.kpi-label {
    font-size: 0.88rem;
    font-weight: 700;
    color: #37474F;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 0.5rem;
}
.kpi-value {
    font-size: 2.3rem;
    font-weight: 700;
    color: #1A237E;
    line-height: 1.1;
    letter-spacing: -0.02em;
}
.kpi-sub {
    font-size: 0.97rem;
    color: #37474F;
    margin-top: 0.45rem;
    font-weight: 500;
}

/* Section headers — tighter spacing */
.section-header {
    font-size: 1.15rem;
    font-weight: 700;
    color: #1B4F8A;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 1.1rem 0 0.5rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 3px solid #1B4F8A;
}

/* Insight / callout boxes */
.callout {
    border-radius: 8px;
    padding: 1.2rem 1.5rem;
    margin: 0.6rem 0;
    font-size: 1.05rem;
    line-height: 1.8;
    border-left: 5px solid transparent;
    border-top: 1px solid transparent;
    border-right: 1px solid transparent;
    border-bottom: 1px solid transparent;
}
.callout-blue {
    background: #E3F2FD;
    border-color: #1565C0;
    border-left-color: #1565C0;
    color: #0D47A1;
}
.callout-green {
    background: #E8F5E9;
    border-color: #2E7D32;
    border-left-color: #2E7D32;
    color: #1B5E20;
}
.callout-orange {
    background: #FFF3E0;
    border-color: #E65100;
    border-left-color: #E65100;
    color: #7F3000;
}
.callout-red {
    background: #FFEBEE;
    border-color: #C62828;
    border-left-color: #C62828;
    color: #7F0000;
}
.callout-purple {
    background: #EDE7F6;
    border-color: #4527A0;
    border-left-color: #4527A0;
    color: #311B92;
}
.callout-label {
    font-weight: 700;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.5rem;
    display: block;
}

/* Chart card wrapper */
.chart-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 1.4rem 1.5rem 0.6rem 1.5rem;
    border: 1px solid #BBDEFB;
    box-shadow: 0 2px 8px rgba(27,79,138,0.08);
    margin-bottom: 1rem;
}
.chart-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #1A237E;
    margin-bottom: 0.3rem;
}
.chart-caption {
    font-size: 0.95rem;
    color: #263238;
    margin-bottom: 0.9rem;
    line-height: 1.6;
}

/* Table styling */
.stDataFrame {
    border: 1px solid #BBDEFB !important;
    border-radius: 8px !important;
    font-size: 1.02rem !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    border-bottom: 3px solid #1B4F8A;
}
.stTabs [data-baseweb="tab"] {
    font-size: 1.02rem;
    font-weight: 600;
    color: #263238;
    padding: 0.6rem 1.3rem;
    border-radius: 6px 6px 0 0;
    border: 1px solid transparent;
}
.stTabs [aria-selected="true"] {
    color: #1B4F8A !important;
    background-color: #E3F2FD !important;
    border-color: #BBDEFB !important;
    border-bottom-color: #E3F2FD !important;
}

/* Status badge */
.badge {
    display: inline-block;
    padding: 0.3rem 1rem;
    border-radius: 20px;
    font-size: 0.88rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    border: 1px solid transparent;
}
.badge-red    { background:#FFEBEE; color:#B71C1C; border-color:#FFCDD2; }
.badge-orange { background:#FFF3E0; color:#7F3000; border-color:#FFE0B2; }
.badge-green  { background:#E8F5E9; color:#1B5E20; border-color:#C8E6C9; }
.badge-blue   { background:#E3F2FD; color:#0D47A1; border-color:#BBDEFB; }
.badge-grey   { background:#ECEFF1; color:#263238; border-color:#CFD8DC; }

/* Divider */
.divider {
    border: none;
    border-top: 2px solid #BBDEFB;
    margin: 1.2rem 0;
}

/* Metric delta override */
[data-testid="stMetricDelta"] { font-size: 1.05rem; }
[data-testid="stMetricValue"] { font-size: 2.1rem !important; font-weight: 700; color: #1A237E; }
[data-testid="stMetricLabel"] { font-size: 0.92rem !important; font-weight: 700; color: #263238 !important; text-transform: uppercase; letter-spacing: 0.05em; }

/* Expander — strong visible border and colored header */
[data-testid="stExpander"] {
    border: 2px solid #1B4F8A !important;
    border-radius: 10px !important;
    background: #FFFFFF !important;
    margin-bottom: 0.8rem !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] > details {
    background: #FFFFFF !important;
}
[data-testid="stExpander"] > details > summary,
[data-testid="stExpander"] summary {
    background: #1B4F8A !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 0.9rem 1.2rem !important;
    cursor: pointer !important;
    list-style: none !important;
}
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary div,
.streamlit-expanderHeader,
.streamlit-expanderHeader p,
.streamlit-expanderHeader span {
    font-size: 1.08rem !important;
    font-weight: 700 !important;
    color: #FFFFFF !important;
}
[data-testid="stExpander"] svg {
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
}
/* Expander body — light blue bg, dark text */
[data-testid="stExpander"] > details > div,
[data-testid="stExpander"] .streamlit-expanderContent {
    background: #F8FBFF !important;
    padding: 1rem 1.2rem !important;
    border-top: 1px solid #BBDEFB !important;
}
[data-testid="stExpander"] .stMarkdown p,
[data-testid="stExpander"] p,
[data-testid="stExpander"] li {
    color: #1A237E !important;
    font-size: 1.02rem !important;
    line-height: 1.8 !important;
}
[data-testid="stExpander"] table {
    font-size: 1.02rem !important;
    color: #263238 !important;
    width: 100%;
    border-collapse: collapse;
}
[data-testid="stExpander"] th {
    background: #1B4F8A !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    padding: 0.6rem 1rem !important;
    text-align: left !important;
}
[data-testid="stExpander"] td {
    padding: 0.5rem 1rem !important;
    border-bottom: 1px solid #BBDEFB !important;
    color: #263238 !important;
}
[data-testid="stExpander"] tr:nth-child(even) td {
    background: #E3F2FD !important;
}

/* General body text — exclude page-header so white text is not overridden */
p:not(.page-header p), li, .stMarkdown p {
    font-size: 1.02rem !important;
    color: #263238 !important;
    line-height: 1.8;
}

/* Markdown text inside columns and containers — exclude page-header */
.stMarkdown:not(.page-header .stMarkdown),
.element-container .stMarkdown:not(.page-header .stMarkdown) {
    color: #263238 !important;
}

/* Page header text — force white always, highest specificity */
div.page-header *,
div.page-header p,
div.page-header div,
div.page-header span {
    color: #FFFFFF !important;
    font-size: inherit !important;
}

/* Year filter toggle buttons */
.year-filter-wrap {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: #FFFFFF;
    border: 1.5px solid #BBDEFB;
    border-radius: 10px;
    padding: 0.6rem 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 6px rgba(27,79,138,0.08);
}
.year-filter-label {
    font-size: 0.88rem;
    font-weight: 700;
    color: #1B4F8A;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-right: 0.5rem;
    white-space: nowrap;
}
.year-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.38rem 1.1rem;
    border-radius: 6px;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    border: 2px solid #1B4F8A;
    background: #FFFFFF;
    color: #1B4F8A;
    transition: all 0.15s ease;
    user-select: none;
    font-family: Inter, Segoe UI, Arial, sans-serif;
}
.year-btn.active {
    background: #1B4F8A;
    color: #FFFFFF;
    box-shadow: 0 2px 6px rgba(27,79,138,0.25);
}
.year-btn:hover:not(.active) {
    background: #E3F2FD;
}

/* Slider / select labels */
[data-testid="stSlider"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stSelectbox"] label {
    font-size: 1.02rem !important;
    font-weight: 600 !important;
    color: #1A237E !important;
}

/* Tab content text */
[data-testid="stTabContent"] p,
[data-testid="stTabContent"] li {
    color: #263238 !important;
    font-size: 1.02rem !important;
}

/* Button */
.stButton button {
    background-color: #1B4F8A;
    color: white;
    border: 2px solid #1B4F8A;
    border-radius: 8px;
    font-weight: 700;
    font-size: 1.02rem;
    padding: 0.7rem 1.6rem;
}
.stButton button:hover {
    background-color: #1565C0;
    border-color: #1565C0;
}
</style>
"""


def apply_theme():
    """Call at the top of every page after set_page_config."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    """Render the standard page header banner."""
    st.markdown(f"""
    <div class="page-header" style="background:linear-gradient(135deg,#1B4F8A 0%,#1565C0 100%);
                padding:1.8rem 2rem;border-radius:12px;margin-bottom:1.2rem;
                box-shadow:0 3px 10px rgba(27,79,138,0.22);">
        <div style="color:#FFFFFF !important;font-size:1.9rem;font-weight:700;
                    margin:0 0 0.3rem 0;letter-spacing:-0.02em;
                    font-family:Inter,Segoe UI,Arial,sans-serif;
                    line-height:1.2;">{title}</div>
        <div style="color:#FFFFFF !important;font-size:1.08rem;font-weight:400;
                    font-family:Inter,Segoe UI,Arial,sans-serif;
                    opacity:0.92;margin-top:0.2rem;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def section_header(text: str):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "", color: str = "blue") -> str:
    color_class = {"blue": "", "green": "green", "red": "red",
                   "orange": "orange", "purple": "purple", "teal": "teal"}.get(color, "")
    return f"""
    <div class="kpi-card {color_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {"<div class='kpi-sub'>" + sub + "</div>" if sub else ""}
    </div>"""


def callout(text: str, kind: str = "blue", label: str = ""):
    label_html = f'<span class="callout-label">{label}</span>' if label else ""
    return f'<div class="callout callout-{kind}">{label_html}{text}</div>'


def badge(text: str, kind: str = "grey") -> str:
    return f'<span class="badge badge-{kind}">{text}</span>'


def chart_card_open(title: str, caption: str = "") -> str:
    cap_html = f'<div class="chart-caption">{caption}</div>' if caption else ""
    return f'<div class="chart-card"><div class="chart-title">{title}</div>{cap_html}'


def chart_card_close() -> str:
    return '</div>'
