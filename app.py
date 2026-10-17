"""
Macroeconomic & Interest Rate Dashboard
Author: Finance Assignment Project
Data Source: Federal Reserve Bank of St. Louis (FRED API)
"""

import os
import datetime
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

# ---------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="Macroeconomic & Interest Rate Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished terminal-like finance UI
st.markdown("""
<style>
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .badge-inversion {
        background-color: #ff4b4b22;
        color: #ff4b4b;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .badge-normal {
        background-color: #00c85322;
        color: #00c853;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0px 0px;
        padding: 8px 16px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Environment & Configuration
# ---------------------------------------------------------
load_dotenv()
ENV_FRED_API_KEY = os.getenv("FRED_API_KEY", "").strip()

SERIES_METADATA = {
    "FEDFUNDS": {
        "name": "Federal Funds Effective Rate",
        "unit": "%",
        "description": "The interest rate at which depository institutions lend reserve balances to other depository institutions overnight."
    },
    "CPIAUCSL": {
        "name": "Consumer Price Index (CPI-U)",
        "unit": "Index (1982-1984=100)",
        "description": "Monthly measure of average change over time in prices paid by urban consumers for a market basket of goods and services."
    },
    "UNRATE": {
        "name": "Unemployment Rate",
        "unit": "%",
        "description": "Percentage of the total labor force that is unemployed but actively seeking employment."
    },
    "GS10": {
        "name": "10-Year Treasury Yield",
        "unit": "%",
        "description": "10-Year Treasury Constant Maturity rate, representing long-term benchmark government borrowing costs."
    },
    "GS2": {
        "name": "2-Year Treasury Yield",
        "unit": "%",
        "description": "2-Year Treasury Constant Maturity rate, highly sensitive to market expectations of near-term Federal Reserve rate policy."
    },
    "TB3MS": {
        "name": "3-Month Treasury Bill Rate",
        "unit": "%",
        "description": "3-Month Treasury Bill Secondary Market Rate, benchmark for short-term risk-free rates."
    }
}

# ---------------------------------------------------------
# Helper Functions: Offline Realistic Sample Generator
# ---------------------------------------------------------
def generate_sample_data() -> pd.DataFrame:
    """
    Generates realistic historical macroeconomic data spanning from 1990 to recent months.
    Emulates historical patterns:
    - 1990s expansion and Fed rate movements
    - 2001 dot-com recession & yield inversions
    - 2007-2008 Great Financial Crisis & zero lower bound
    - 2020 COVID shock & 2022-2023 inflation spike + yield curve inversion
    """
    dates = pd.date_range(start="1990-01-01", end="2024-06-01", freq="MS")
    n = len(dates)
    np.random.seed(42)

    # Base index
    cpi_vals = []
    current_cpi = 130.0
    
    # Synthetic series tailored to approximate real historical trends
    fed_list = []
    gs10_list = []
    gs2_list = []
    tb3_list = []
    unrate_list = []
    
    for i, d in enumerate(dates):
        year = d.year + (d.month - 1) / 12.0
        
        # Approximate historical Fed Funds regime
        if year < 1995:
            base_ff = 5.0 - (year - 1990) * 0.4
            base_un = 6.8 - (year - 1990) * 0.3
            base_infl = 3.2
        elif year < 2001:
            base_ff = 5.5 + 0.3 * np.sin(year)
            base_un = 4.5 - (year - 1995) * 0.1
            base_infl = 2.4
        elif year < 2004:
            base_ff = 1.75 - (year - 2001) * 0.2
            base_un = 5.8
            base_infl = 2.0
        elif year < 2008:
            base_ff = 4.8 + 0.2 * np.sin(year)
            base_un = 4.8
            base_infl = 3.4
        elif year < 2016:
            base_ff = 0.15
            base_un = 8.5 - (year - 2009) * 0.6 if year > 2009 else 6.0 + (year - 2008) * 3.0
            base_infl = 1.6
        elif year < 2020:
            base_ff = 1.8 + 0.4 * (year - 2016)
            base_un = 3.9
            base_infl = 2.1
        elif year < 2022:
            base_ff = 0.10
            base_un = 6.0 if year < 2021 else 4.2
            base_infl = 4.8 if year > 2021 else 2.5
        else: # 2022-2024
            base_ff = 5.33
            base_un = 3.8
            base_infl = 3.5

        noise = np.random.normal(0, 0.05)
        ff = max(0.05, base_ff + noise)
        tb3 = max(0.05, ff * 0.96 + np.random.normal(0, 0.04))
        
        # Term premium and inversion mechanics
        if (1999.5 <= year <= 2000.8) or (2006.0 <= year <= 2007.5) or (year >= 2022.5):
            # Inversion regime: GS2 > GS10
            gs2 = ff + 0.15 + np.random.normal(0, 0.06)
            gs10 = gs2 - 0.55 + np.random.normal(0, 0.05)
        else:
            # Normal upward sloping regime
            gs2 = max(0.2, ff * 0.85 + 0.4 + np.random.normal(0, 0.05))
            gs10 = max(0.8, gs2 + 0.9 + np.random.normal(0, 0.06))

        un = max(3.4, base_un + np.random.normal(0, 0.08))
        
        # Monthly CPI step
        monthly_cpi_rate = (base_infl / 100.0) / 12.0 + np.random.normal(0, 0.001)
        current_cpi *= (1.0 + monthly_cpi_rate)
        
        fed_list.append(round(ff, 2))
        gs10_list.append(round(gs10, 2))
        gs2_list.append(round(gs2, 2))
        tb3_list.append(round(tb3, 2))
        unrate_list.append(round(un, 1))
        cpi_vals.append(round(current_cpi, 2))

    df = pd.DataFrame({
        "date": dates,
        "FEDFUNDS": fed_list,
        "CPIAUCSL": cpi_vals,
        "UNRATE": unrate_list,
        "GS10": gs10_list,
        "GS2": gs2_list,
        "TB3MS": tb3_list
    })
    return df

# ---------------------------------------------------------
# FRED API Fetcher
# ---------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fred_series(series_id: str, api_key: str, start_date: str = "1960-01-01") -> pd.DataFrame:
    """
    Fetches historical observations for a single series from the FRED API.
    Raises exceptions for HTTP errors or invalid responses.
    """
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date
    }
    
    response = requests.get(url, params=params, timeout=12)
    response.raise_for_status()
    data = response.json()
    
    if "observations" not in data:
        error_msg = data.get("error_message", "Unexpected response from FRED API")
        raise ValueError(f"FRED API Error ({series_id}): {error_msg}")
        
    obs = data["observations"]
    if not obs:
        raise ValueError(f"No observations returned for {series_id}")
        
    df = pd.DataFrame(obs)[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    # FRED uses '.' to represent missing data
    df[series_id] = pd.to_numeric(df["value"].replace(".", np.nan), errors="coerce")
    return df[["date", series_id]]

def load_all_macro_data(api_key: str, use_demo: bool):
    """
    Loads data either from live FRED API or offline synthetic dataset.
    Returns: (df, data_source_type, error_messages)
    """
    is_placeholder = (
        not api_key or
        api_key == "YOUR_FRED_API_KEY_HERE" or
        len(api_key.strip()) < 10
    )
    
    if use_demo or is_placeholder:
        df = generate_sample_data()
        df["date"] = pd.to_datetime(df["date"])
        source_label = "Demo Sample Data" if use_demo else "Offline Sample Data (No API Key Provided)"
        return df, source_label, None

    # Fetch live series
    series_ids = list(SERIES_METADATA.keys())
    merged_df = None
    errors = []
    
    for sid in series_ids:
        try:
            sdf = fetch_fred_series(sid, api_key)
            if merged_df is None:
                merged_df = sdf
            else:
                merged_df = pd.merge(merged_df, sdf, on="date", how="outer")
        except Exception as e:
            errors.append(f"{sid}: {str(e)}")
            
    if errors or merged_df is None or merged_df.empty:
        # Fallback to sample data with clear error details
        fallback_df = generate_sample_data()
        fallback_df["date"] = pd.to_datetime(fallback_df["date"])
        return fallback_df, "Offline Sample Data (API Fetch Failed)", errors

    # Clean and sort
    merged_df = merged_df.sort_values("date").reset_index(drop=True)
    # Forward fill gaps up to 3 months for monthly alignment
    merged_df = merged_df.ffill(limit=3)
    
    return merged_df, "Live FRED API", None

# ---------------------------------------------------------
# Sidebar Controls & Key Settings
# ---------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Dashboard Settings")
    
    st.subheader("FRED API Configuration")
    user_api_key = st.text_input(
        "FRED API Key",
        value="" if ENV_FRED_API_KEY == "YOUR_FRED_API_KEY_HERE" else ENV_FRED_API_KEY,
        type="password",
        help="Enter your 32-character FRED API key. If empty or invalid, the app uses realistic sample data."
    )
    
    effective_api_key = user_api_key.strip() if user_api_key.strip() else ENV_FRED_API_KEY
    
    force_demo = st.checkbox("Force Offline Demo Mode", value=False, help="Toggle on to test the app using offline sample data without making API requests.")
    
    with st.expander("ℹ️ How to get a FRED API Key"):
        st.markdown("""
        1. Create a free account at [FRED St. Louis](https://fred.stlouisfed.org/).
        2. Navigate to **My Account** > **API Keys**.
        3. Request an API key (instant approval).
        4. Paste it above or add `FRED_API_KEY=your_key` in the `.env` file.
        """)
        
    st.divider()
    
    if st.button("🔄 Clear Cache & Reload Data", width="stretch"):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------
# Data Processing & Indicator Math
# ---------------------------------------------------------
raw_df, source_label, api_errors = load_all_macro_data(effective_api_key, force_demo)

# Calculate financial indicators
processed_df = raw_df.copy()

# 1. YoY Inflation Rate: ((CPI_t - CPI_t-12) / CPI_t-12) * 100
# Ensure CPI series is sorted by date before shift
processed_df = processed_df.sort_values("date").reset_index(drop=True)
if "CPIAUCSL" in processed_df.columns:
    processed_df["YoY_Inflation"] = (
        (processed_df["CPIAUCSL"] - processed_df["CPIAUCSL"].shift(12)) /
        processed_df["CPIAUCSL"].shift(12)
    ) * 100.0

# 2. 10Y - 2Y Treasury Yield Spread: GS10 - GS2
if "GS10" in processed_df.columns and "GS2" in processed_df.columns:
    processed_df["T10Y2Y_Spread"] = processed_df["GS10"] - processed_df["GS2"]

# Valid rows for analysis (drop rows where all key series are NaN)
clean_df = processed_df.dropna(subset=["FEDFUNDS", "GS10", "GS2", "TB3MS", "UNRATE"], how="all").copy()

# Date range boundaries
min_year = int(clean_df["date"].dt.year.min())
max_year = int(clean_df["date"].dt.year.max())

# Sidebar Filter: Start Year Slider
with st.sidebar:
    st.subheader("📅 Time Horizon")
    default_start_year = max(min_year, 2000)
    selected_start_year = st.slider(
        "Select Start Year",
        min_value=min_year,
        max_value=max_year,
        value=default_start_year,
        step=1,
        help="Adjust the start year for the historical trend analysis."
    )
    
    st.caption(f"Showing data from **{selected_start_year}** to **{max_year}**.")

# Filter dataset based on slider
filtered_df = clean_df[clean_df["date"].dt.year >= selected_start_year].copy()

# ---------------------------------------------------------
# Main UI Header & Status Banner
# ---------------------------------------------------------
st.title("Macroeconomic & Interest Rate Dashboard")
st.markdown("An interactive macroeconomic terminal monitoring monetary policy, inflation dynamics, labor markets, and yield curve inversion signals.")

# Status Banner
if source_label.startswith("Live FRED"):
    st.success(f"🟢 **Connected:** Utilizing live data from the Federal Reserve Bank of St. Louis (FRED API).")
elif "API Fetch Failed" in source_label:
    st.warning(f"⚠️ **Notice:** Failed to fetch live data from FRED API. Reverted to offline demo data.")
    if api_errors:
        with st.expander("View API Error Details"):
            for err in api_errors:
                st.code(err)
else:
    st.info(f"💡 **Demo Mode:** Operating on realistic macroeconomic reference data. (Provide a valid FRED API key in `.env` or sidebar to stream live updates).")

# ---------------------------------------------------------
# Top KPI Cards
# ---------------------------------------------------------
st.markdown("### 📊 Key Macroeconomic Indicators")

# Helper to grab latest valid value and delta (1-month change)
def get_latest_metric(series_col: str):
    s = clean_df.dropna(subset=[series_col])
    if len(s) == 0:
        return None, None, None
    latest_val = s[series_col].iloc[-1]
    latest_date = s["date"].iloc[-1]
    delta = None
    if len(s) >= 2:
        prev_val = s[series_col].iloc[-2]
        delta = latest_val - prev_val
    return latest_val, delta, latest_date

ff_val, ff_delta, ff_date = get_latest_metric("FEDFUNDS")
cpi_val, cpi_delta, cpi_date = get_latest_metric("YoY_Inflation")
un_val, un_delta, un_date = get_latest_metric("UNRATE")
gs10_val, gs10_delta, gs10_date = get_latest_metric("GS10")

kpi_cols = st.columns(4)

with kpi_cols[0]:
    delta_str = f"{ff_delta:+.2f}% MoM" if ff_delta is not None else None
    st.metric(
        label="Federal Funds Rate (FEDFUNDS)",
        value=f"{ff_val:.2f}%" if ff_val is not None else "N/A",
        delta=delta_str,
        help="Target overnight borrowing rate set by the Federal Open Market Committee (FOMC)."
    )
    if ff_date:
        st.caption(f"As of: {ff_date.strftime('%b %Y')}")

with kpi_cols[1]:
    delta_str = f"{cpi_delta:+.2f}% MoM" if cpi_delta is not None else None
    st.metric(
        label="YoY CPI Inflation Rate",
        value=f"{cpi_val:.2f}%" if cpi_val is not None else "N/A",
        delta=delta_str,
        delta_color="inverse", # Rising inflation is typically considered a pressure
        help="Annual percentage change in Consumer Price Index for All Urban Consumers (CPIAUCSL)."
    )
    if cpi_date:
        st.caption(f"As of: {cpi_date.strftime('%b %Y')}")

with kpi_cols[2]:
    delta_str = f"{un_delta:+.1f}% MoM" if un_delta is not None else None
    st.metric(
        label="Unemployment Rate (UNRATE)",
        value=f"{un_val:.1f}%" if un_val is not None else "N/A",
        delta=delta_str,
        delta_color="inverse",
        help="Percentage of labor force actively seeking employment."
    )
    if un_date:
        st.caption(f"As of: {un_date.strftime('%b %Y')}")

with kpi_cols[3]:
    delta_str = f"{gs10_delta:+.2f}% MoM" if gs10_delta is not None else None
    st.metric(
        label="10-Year Treasury Yield (GS10)",
        value=f"{gs10_val:.2f}%" if gs10_val is not None else "N/A",
        delta=delta_str,
        help="Benchmark long-term sovereign bond yield influencing mortgages and corporate borrowing."
    )
    if gs10_date:
        st.caption(f"As of: {gs10_date.strftime('%b %Y')}")

st.divider()

# ---------------------------------------------------------
# Interactive Multi-Select Trend Chart
# ---------------------------------------------------------
st.markdown("### 📈 Historical Multi-Indicator Trend Comparison")

# Options mapping: Column -> Display Name
INDICATOR_OPTIONS = {
    "FEDFUNDS": "Federal Funds Rate (%)",
    "YoY_Inflation": "YoY CPI Inflation Rate (%)",
    "UNRATE": "Unemployment Rate (%)",
    "GS10": "10-Yr Treasury Yield (GS10) (%)",
    "GS2": "2-Yr Treasury Yield (GS2) (%)",
    "TB3MS": "3-Month T-Bill Rate (TB3MS) (%)",
    "T10Y2Y_Spread": "10Y - 2Y Treasury Yield Spread (%)"
}

default_selection = ["FEDFUNDS", "YoY_Inflation", "GS10"]

selected_indicators = st.multiselect(
    "Select Macroeconomic Indicators to Display:",
    options=list(INDICATOR_OPTIONS.keys()),
    default=default_selection,
    format_func=lambda x: INDICATOR_OPTIONS.get(x, x),
    help="Select one or multiple macroeconomic series to overlay on the trend chart."
)

if not selected_indicators:
    st.info("Please select at least one indicator from the dropdown above to display the chart.")
else:
    trend_fig = go.Figure()
    
    color_palette = px.colors.qualitative.Plotly
    
    for idx, ind in enumerate(selected_indicators):
        if ind in filtered_df.columns:
            series_data = filtered_df.dropna(subset=["date", ind])
            trend_fig.add_trace(go.Scatter(
                x=series_data["date"],
                y=series_data[ind],
                mode="lines",
                name=INDICATOR_OPTIONS[ind],
                line=dict(width=2.4, color=color_palette[idx % len(color_palette)]),
                hovertemplate="<b>%{fullData.name}</b><br>Date: %{x|%b %Y}<br>Value: %{y:.2f}%<extra></extra>"
            ))
            
    # Add a horizontal zero reference line if the 10Y-2Y spread is selected
    if "T10Y2Y_Spread" in selected_indicators:
        trend_fig.add_hline(
            y=0.0,
            line_dash="dot",
            line_color="rgba(255, 75, 75, 0.6)",
            annotation_text="Inversion Line (0.0%)",
            annotation_position="bottom right"
        )
        
    trend_fig.update_layout(
        title=f"Macroeconomic Trends ({selected_start_year} - Present)",
        xaxis_title="Date",
        yaxis_title="Percent (%) / Rate",
        hovermode="x unified",
        template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        height=500
    )
    
    st.plotly_chart(trend_fig, width="stretch")

st.divider()

# ---------------------------------------------------------
# Treasury Yield Curve & Inversion Analysis Section
# ---------------------------------------------------------
st.markdown("### 🏛️ Treasury Yield Curve & 10Y - 2Y Spread Analysis")

yield_curve_cols = st.columns([1, 1])

# Extract latest yield curve points
latest_curve_row = clean_df.dropna(subset=["TB3MS", "GS2", "GS10"]).iloc[-1]
latest_curve_date = latest_curve_row["date"]
latest_spread = latest_curve_row["GS10"] - latest_curve_row["GS2"]

# Compare with 1-year prior if available
one_year_prior_date = latest_curve_date - pd.DateOffset(years=1)
prior_candidates = clean_df[clean_df["date"] <= one_year_prior_date].dropna(subset=["TB3MS", "GS2", "GS10"])
prior_curve_row = prior_candidates.iloc[-1] if not prior_candidates.empty else None

with yield_curve_cols[0]:
    st.subheader("Term Structure of Interest Rates")
    
    maturities = ["3-Month", "2-Year", "10-Year"]
    tenors_numeric = [0.25, 2.0, 10.0]
    
    current_yields = [
        latest_curve_row["TB3MS"],
        latest_curve_row["GS2"],
        latest_curve_row["GS10"]
    ]
    
    yc_fig = go.Figure()
    
    # Current Yield Curve
    yc_fig.add_trace(go.Scatter(
        x=maturities,
        y=current_yields,
        mode="lines+markers+text",
        name=f"Latest ({latest_curve_date.strftime('%b %Y')})",
        line=dict(color="#29b6f6", width=3),
        marker=dict(size=10, color="#0288d1"),
        text=[f"{y:.2f}%" for y in current_yields],
        textposition="top center",
        hovertemplate="Maturity: %{x}<br>Yield: %{y:.2f}%<extra></extra>"
    ))
    
    # Prior Year Yield Curve Comparison
    if prior_curve_row is not None:
        prior_yields = [
            prior_curve_row["TB3MS"],
            prior_curve_row["GS2"],
            prior_curve_row["GS10"]
        ]
        yc_fig.add_trace(go.Scatter(
            x=maturities,
            y=prior_yields,
            mode="lines+markers",
            name=f"1 Year Ago ({prior_curve_row['date'].strftime('%b %Y')})",
            line=dict(color="#ffa726", width=2, dash="dash"),
            marker=dict(size=8, color="#f57c00"),
            hovertemplate="Maturity: %{x}<br>Yield: %{y:.2f}%<extra></extra>"
        ))
        
    yc_fig.update_layout(
        title=f"U.S. Treasury Yield Curve Comparison",
        xaxis_title="Maturity Tenor",
        yaxis_title="Yield (%)",
        template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=50, b=40),
        height=380
    )
    
    st.plotly_chart(yc_fig, width="stretch")

with yield_curve_cols[1]:
    st.subheader("Yield Curve Inversion Monitor")
    
    # Metric display for spread
    st.metric(
        label="10Y - 2Y Spread (GS10 - GS2)",
        value=f"{latest_spread:+.2f}%",
        help="Difference between 10-Year and 2-Year Treasury yields. A negative reading indicates yield curve inversion."
    )
    
    # Conditional Warning Box
    if latest_spread < 0:
        st.error(f"""
        ⚠️ **YIELD CURVE INVERSION DETECTED: {latest_spread:.2f}%**
        
        **Macroeconomic Implication:**
        The 2-Year Treasury yield is currently higher than the 10-Year yield. Inverted yield curves occur when short-term interest rates are elevated by monetary policy while investors anticipate economic cooling and future central bank easing.
        
        Historically, sustained inversions of the 10Y - 2Y spread have preceded every U.S. recession over the past 50 years with an average lag of 12 to 24 months.
        """)
    else:
        st.success(f"""
        ✅ **NORMAL UPWARD-SLOPING YIELD CURVE: +{latest_spread:.2f}%**
        
        **Macroeconomic Implication:**
        The 10-Year Treasury yield exceeds the 2-Year yield. This upward term structure is typical during periods of economic expansion, as bond investors demand higher returns (a term premium) to compensate for inflation and duration risk over longer horizons.
        """)
        
    st.markdown("""
    **Current Maturity Snapshot:**
    - **3-Month T-Bill (TB3MS):** `{:.2f}%`
    - **2-Year Treasury (GS2):** `{:.2f}%`
    - **10-Year Treasury (GS10):** `{:.2f}%`
    """.format(
        latest_curve_row['TB3MS'],
        latest_curve_row['GS2'],
        latest_curve_row['GS10']
    ))

# ---------------------------------------------------------
# Historical 10Y - 2Y Spread Chart
# ---------------------------------------------------------
st.markdown("#### Historical 10Y - 2Y Treasury Yield Spread")

spread_series = filtered_df.dropna(subset=["date", "T10Y2Y_Spread"]).copy()

spread_fig = go.Figure()

# Add zero line
spread_fig.add_hline(
    y=0.0,
    line_dash="dash",
    line_color="#e53935",
    line_width=1.5,
    annotation_text="Zero Inversion Threshold (0.00%)",
    annotation_position="bottom right"
)

# Plot spread line
spread_fig.add_trace(go.Scatter(
    x=spread_series["date"],
    y=spread_series["T10Y2Y_Spread"],
    mode="lines",
    name="10Y - 2Y Spread",
    line=dict(color="#00b0ff", width=2),
    hovertemplate="Date: %{x|%b %Y}<br>Spread: %{y:+.2f}%<extra></extra>"
))

# Highlight inverted periods (< 0) with a red fill
inversion_mask = spread_series["T10Y2Y_Spread"] < 0
if inversion_mask.any():
    spread_fig.add_trace(go.Scatter(
        x=spread_series["date"],
        y=spread_series["T10Y2Y_Spread"].where(inversion_mask, 0),
        mode="lines",
        name="Inverted Zones (< 0%)",
        fill="tozeroy",
        fillcolor="rgba(239, 83, 80, 0.25)",
        line=dict(color="rgba(0,0,0,0)"),
        hoverinfo="skip"
    ))

spread_fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Spread (% Points)",
    template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white",
    margin=dict(l=40, r=40, t=30, b=40),
    height=320,
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(spread_fig, width="stretch")

st.divider()

# ---------------------------------------------------------
# Data Table & Export Section
# ---------------------------------------------------------
with st.expander("📋 View Data Table & Export"):
    st.markdown("Below is the underlying data table for the selected date range. You can inspect values or download the dataset as a CSV.")
    
    display_cols = ["date", "FEDFUNDS", "CPIAUCSL", "YoY_Inflation", "UNRATE", "GS10", "GS2", "TB3MS", "T10Y2Y_Spread"]
    available_cols = [c for c in display_cols if c in filtered_df.columns]
    
    export_df = filtered_df[available_cols].copy()
    export_df = export_df.rename(columns={
        "date": "Date",
        "FEDFUNDS": "Fed_Funds_Rate",
        "CPIAUCSL": "CPI_Index",
        "YoY_Inflation": "YoY_CPI_Inflation_Pct",
        "UNRATE": "Unemployment_Rate",
        "GS10": "Treasury_10Y",
        "GS2": "Treasury_2Y",
        "TB3MS": "TBill_3M",
        "T10Y2Y_Spread": "Spread_10Y_2Y"
    })
    
    st.dataframe(
        export_df.sort_values("Date", ascending=False),
        width="stretch",
        hide_index=True
    )
    
    csv_data = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv_data,
        file_name=f"macro_data_{selected_start_year}_{max_year}.csv",
        mime="text/csv"
    )

# ---------------------------------------------------------
# Financial Methodology & Reference Guide
# ---------------------------------------------------------
with st.expander("📖 Financial Methodology & FRED Series Documentation"):
    st.markdown("""
    ### 1. Year-over-Year (YoY) Inflation Rate Formula
    The Year-over-Year (YoY) Inflation Rate measures the percentage change in the Consumer Price Index (CPI-U) relative to the same month of the previous year (a 12-month lag):
    
    $$\\text{YoY Inflation}_t = \\left(\\frac{\\text{CPI}_t - \\text{CPI}_{t-12}}{\\text{CPI}_{t-12}}\\right) \\times 100$$
    
    - **Series Used:** `CPIAUCSL` (Consumer Price Index for All Urban Consumers: All Items in U.S. City Average, Seasonally Adjusted).
    - **Significance:** YoY inflation filters out regular seasonal price swings and serves as a cornerstone metric for Federal Reserve monetary policy and inflation targeting.

    ---
    ### 2. Treasury Yield Curve Spread (10Y - 2Y) & Inversion Interpretation
    The term structure of interest rates reflects market expectations for growth, inflation, and central bank policy rates across maturities:
    
    $$\\text{Spread} = \\text{GS10} - \\text{GS2}$$
    
    - **Normal Curve (Spread > 0):** Investors demand higher yields on longer maturities to compensate for duration risk, liquidity preference, and inflation uncertainty.
    - **Flat Curve (Spread ≈ 0):** Indicates economic transition or market uncertainty regarding future growth.
    - **Inverted Curve (Spread < 0):** When 2-year yields surpass 10-year yields, it reflects tight monetary policy coupled with expectations of economic deceleration and subsequent central bank easing. An inverted 10Y-2Y yield curve has reliably signaled every U.S. recession over the past half-century.

    ---
    ### 3. FRED Series Reference
    | Series ID | Series Name | Frequency | Units |
    |---|---|---|---|
    | `FEDFUNDS` | Federal Funds Effective Rate | Monthly | Percent |
    | `CPIAUCSL` | Consumer Price Index for All Urban Consumers | Monthly | Index 1982-1984=100 |
    | `UNRATE` | Unemployment Rate | Monthly | Percent |
    | `GS10` | 10-Year Treasury Constant Maturity Rate | Monthly | Percent |
    | `GS2` | 2-Year Treasury Constant Maturity Rate | Monthly | Percent |
    | `TB3MS` | 3-Month Treasury Bill Secondary Market Rate | Monthly | Percent |
    """)

# Footer
st.markdown("---")
st.caption("Macroeconomic & Interest Rate Dashboard | Built for Finance & Macroeconomic Analysis | Data via Federal Reserve Economic Data (FRED)")
