# =========================================
# NYC Citi Bike Dashboard (Streamlit App)
# =========================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

# -----------------------------------------
# Initialize dashboard settings (TOP ONLY)
# -----------------------------------------
st.set_page_config(
    page_title="NYC Citi Bike Dashboard",
    page_icon="🚲",
    layout="wide"
)

# -----------------------------------------
# Dashboard title & description
# -----------------------------------------
st.title("NYC Citi Bike Dashboard")

st.markdown(
    """
    **Purpose of this dashboard**

    This interactive dashboard explores New York City Citi Bike usage patterns
    in relation to weather conditions. It combines trip data with daily
    temperature metrics to highlight station popularity and seasonal trends.
    """
)

# -----------------------------------------
# Kepler.gl Map
# -----------------------------------------

st.markdown("---")
st.subheader("Kepler.gl Map")

kepler_file = Path("Kepler.gl.html")

if kepler_file.exists():
    kepler_html = kepler_file.read_text(encoding="utf-8")
    st.components.v1.html(kepler_html, height=650, scrolling=True)
else:
    st.error("Kepler.gl.html not found. Make sure it is in the same folder.")


# -----------------------------------------
# Load data
# -----------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("citibike_weather_2022.csv")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["TMAX"] = pd.to_numeric(df["TMAX"], errors="coerce")
    df["TMIN"] = pd.to_numeric(df["TMIN"], errors="coerce")
    df["avg_temp"] = (df["TMAX"] + df["TMIN"]) / 2
    return df.dropna(subset=["date", "avg_temp"])

df = load_data()

# -----------------------------------------
# Top stations bar chart
# -----------------------------------------
TOP_N = 20
top_stations = (
    df["start_station_name"]
    .value_counts()
    .head(TOP_N)
    .reset_index()
)
top_stations.columns = ["Station", "Trips"]

st.subheader(f"Top {TOP_N} Most Popular Starting Stations")
st.bar_chart(top_stations.set_index("Station")["Trips"])

# -----------------------------------------
# Dual-axis line chart (Plotly)
# -----------------------------------------
daily_trips = df.groupby("date").size().reset_index(name="trip_count")
daily_temp = df.groupby("date")["avg_temp"].mean().reset_index(name="avg_temp")
daily = pd.merge(daily_trips, daily_temp, on="date").sort_values("date")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=daily["date"].to_numpy(),
    y=daily["trip_count"],
    name="Daily Bike Trips",
    mode="lines",
    yaxis="y1"
))

fig.add_trace(go.Scatter(
    x=daily["date"].to_numpy(),
    y=daily["avg_temp"],
    name="Average Temperature",
    mode="lines",
    yaxis="y2"
))

fig.update_layout(
    title="Daily Bike Trips and Average Temperature (Dual Axis)",
    title_x=0.5,
    template="plotly_white",
    height=550,
    hovermode="x unified",
    xaxis=dict(title="Date"),
    yaxis=dict(title="Number of Bike Trips"),
    yaxis2=dict(title="Average Temperature", overlaying="y", side="right")
)

st.subheader("Trips vs Temperature Over Time")
st.plotly_chart(fig, use_container_width=True)
