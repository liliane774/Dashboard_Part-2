import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt

# --------------------------------------------------
# App configuration
# --------------------------------------------------
st.set_page_config(
    page_title="NYC CitiBike Dashboard (2022)",
    layout="wide",
    initial_sidebar_state="expanded"   # sidebar open so navigation is easy
)

# Make iframe/map responsive and avoid overlap (remove negative margins!)
st.markdown(
    """
    <style>
    iframe {
        width: 100% !important;
        height: 650px !important;
        min-height: 650px !important;
        margin-bottom: 0px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# Helper: SAFE Matplotlib display (full-width)
# --------------------------------------------------
def st_mpl(fig):
    """
    Streamlit-compatible Matplotlib display.
    Works even if st.image() does NOT support use_container_width.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)

    # Older Streamlit: no use_container_width argument
    try:
        st.image(buf, use_container_width=True)   # newer Streamlit
    except TypeError:
        st.image(buf)                             # older Streamlit fallback

    plt.close(fig)


# --------------------------------------------------
# Load reduced sample dataset
# --------------------------------------------------
@st.cache_data
def load_data():
    return pd.read_csv("citibike_weather_sample.csv", low_memory=False)

df = load_data()

# --------------------------------------------------
# Sidebar navigation (Pages)
# --------------------------------------------------
page = st.sidebar.selectbox(
    "Choose a page",
    [
        "Intro",
        "Overview",
        "Trips & Time Trends",
        "Dual-Axis: Trips vs Temperature",
        "Popular Stations",
        "Weather Impact",
        "Stations & Routes",
        "Kepler.gl Map",
        "Station Balance (Supply Problem)"
    ]
)

# --------------------------------------------------
# Intro Page
# --------------------------------------------------
if page == "Intro":
    st.title("NYC CitiBike Dashboard (2022)")

    st.write(
        """
        This dashboard explores New York City Citi Bike trip activity and how ride behavior
        changes across time, stations and routes, rider type, and weather conditions.
        The purpose is to support strategy decisions such as identifying peak demand periods,
        high-value locations, and potential weather-related demand shifts.
        """
    )

    img_url = "https://commons.wikimedia.org/wiki/Special:FilePath/The_City_with_Citi_Bikes.jpg"
    st.image(
        img_url,
        caption="Citi Bike docking station in NYC. Photo by Alan Levine (CC BY-SA, Wikimedia Commons)",
        width=900
    )

    st.subheader("How to use this dashboard")
    st.write(
        """
        Use the sidebar to navigate between pages:
        - **Overview**: Dataset preview and basic metrics
        - **Trips & Time Trends**: Trip activity patterns over time
        - **Dual-Axis**: Trips vs temperature over time
        - **Weather Impact**: Weather vs trip volume
        - **Stations & Routes / Popular Stations**: Key demand hubs
        - **Kepler.gl Map**: Interactive spatial visualization
        - **Station Balance**: Stations that lose/gain bikes (rebalancing)
        """
    )

    st.info(
        "Data note: This dashboard uses a reproducible sample kept under 25 MB to ensure performance."
    )

# --------------------------------------------------
# Overview Page
# --------------------------------------------------
elif page == "Overview":
    st.title("Overview")
    st.write("Preview of the reduced Citi Bike dataset:")
    st.dataframe(df.head(20), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Number of Rows", f"{len(df):,}")
    with col2:
        st.metric("Number of Columns", f"{df.shape[1]:,}")

# --------------------------------------------------
# Trips & Time Trends Page
# --------------------------------------------------
elif page == "Trips & Time Trends":
    st.title("Trips & Time Trends")
    st.write("This page shows daily, monthly, and hourly trip patterns.")

    if "started_at" not in df.columns:
        st.error("Missing required column: started_at")
        st.stop()

    df_time = df.copy()
    df_time["started_at"] = pd.to_datetime(df_time["started_at"], errors="coerce")
    df_time = df_time.dropna(subset=["started_at"])

    df_time["date"] = df_time["started_at"].dt.floor("D")
    df_time["month"] = df_time["started_at"].dt.month
    df_time["hour"] = df_time["started_at"].dt.hour

    min_date = df_time["date"].min().date()
    max_date = df_time["date"].max().date()

    start_d, end_d = st.sidebar.date_input(
        "Date range (Trips page)",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    rider_filter = "All"
    if "member_casual" in df_time.columns:
        rider_filter = st.sidebar.selectbox("Rider type (Trips page)", ["All", "member", "casual"])

    mask = (df_time["date"].dt.date >= start_d) & (df_time["date"].dt.date <= end_d)
    df_time = df_time.loc[mask]

    if rider_filter != "All" and "member_casual" in df_time.columns:
        df_time = df_time[df_time["member_casual"] == rider_filter]

    daily = df_time.groupby("date").size().reset_index(name="trip_count").sort_values("date")

    # month order 1..12
    monthly = df_time.groupby("month").size().reindex(range(1, 13), fill_value=0)
    hourly = df_time.groupby("hour").size().reindex(range(24), fill_value=0)

    col1, col2, col3 = st.columns(3)
    col1.metric("Trips (filtered)", f"{len(df_time):,}")
    col2.metric("Avg trips / day", f"{daily['trip_count'].mean():,.0f}" if len(daily) else "0")
    col3.metric("Peak hour", f"{int(hourly.idxmax()):02d}:00" if hourly.sum() else "N/A")

    st.subheader("Daily Trip Volume")
    fig1, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(daily["date"], daily["trip_count"])
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Trips")
    fig1.autofmt_xdate()
    st_mpl(fig1)

    st.subheader("Trips by Month")
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.bar([month_names[m-1] for m in monthly.index], monthly.values)
    ax2.set_ylabel("Trips")
    ax2.set_xlabel("Month")
    st_mpl(fig2)

    st.subheader("Trips by Hour of Day")
    fig3, ax3 = plt.subplots(figsize=(10, 4))
    ax3.bar(hourly.index, hourly.values)
    ax3.set_xlabel("Hour (0–23)")
    ax3.set_ylabel("Trips")
    st_mpl(fig3)

    with st.expander("Interpretation"):
        st.markdown(
            """
            The daily trend shows demand fluctuations with peaks that indicate higher ridership periods,
            which can increase pressure on bike availability at popular stations.

            Monthly patterns suggest seasonality, with higher ridership in warmer months and lower demand
            in colder periods. Hourly patterns reveal demand concentrations at specific times, which is
            useful for planning **rebalancing operations** and staffing.
            """
        )

# --------------------------------------------------
# Dual-Axis Page
# --------------------------------------------------
elif page == "Dual-Axis: Trips vs Temperature":
    st.title("Trips vs Temperature Over Time")
    st.write(
        "This chart compares daily trip volume with average daily temperature "
        "to highlight seasonal and weather-related patterns."
    )

    required_cols = ["started_at", "TMAX", "TMIN"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        st.stop()

    df_time = df.copy()
    df_time["started_at"] = pd.to_datetime(df_time["started_at"], errors="coerce")
    df_time["TMAX"] = pd.to_numeric(df_time["TMAX"], errors="coerce")
    df_time["TMIN"] = pd.to_numeric(df_time["TMIN"], errors="coerce")
    df_time = df_time.dropna(subset=["started_at", "TMAX", "TMIN"])

    df_time["avg_temp"] = (df_time["TMAX"] + df_time["TMIN"]) / 2
    df_time["date"] = df_time["started_at"].dt.floor("D")

    # if ride_id doesn't exist, count rows instead
    if "ride_id" in df_time.columns:
        daily_summary = df_time.groupby("date").agg(
            trip_count=("ride_id", "count"),
            avg_temp=("avg_temp", "mean")
        ).reset_index().sort_values("date")
    else:
        daily_summary = df_time.groupby("date").agg(
            trip_count=("date", "size"),
            avg_temp=("avg_temp", "mean")
        ).reset_index().sort_values("date")

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(daily_summary["date"], daily_summary["trip_count"])
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Trips")

    ax2 = ax1.twinx()
    ax2.plot(daily_summary["date"], daily_summary["avg_temp"], linestyle="--")
    ax2.set_ylabel("Avg Temperature")

    fig.autofmt_xdate()
    st_mpl(fig)

    with st.expander("Interpretation"):
        st.markdown(
            """
            Trip volume generally rises as average temperatures increase, suggesting stronger ridership
            during warmer periods. Colder conditions correspond with reduced usage. This supports using
            seasonal forecasting to guide operations and availability planning.
            """
        )

# --------------------------------------------------
# Weather Impact Page
# --------------------------------------------------
elif page == "Weather Impact":
    st.title("Weather Impact")
    st.write("This page analyzes how weather variables relate to trip volume.")

    required_cols = ["started_at", "TMAX", "TMIN", "PRCP"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        st.stop()

    df_w = df.copy()
    df_w["started_at"] = pd.to_datetime(df_w["started_at"], errors="coerce")
    df_w["TMAX"] = pd.to_numeric(df_w["TMAX"], errors="coerce")
    df_w["TMIN"] = pd.to_numeric(df_w["TMIN"], errors="coerce")
    df_w["PRCP"] = pd.to_numeric(df_w["PRCP"], errors="coerce")
    df_w = df_w.dropna(subset=["started_at", "TMAX", "TMIN", "PRCP"])

    df_w["avg_temp"] = (df_w["TMAX"] + df_w["TMIN"]) / 2
    df_w["date"] = df_w["started_at"].dt.floor("D")

    min_date = df_w["date"].min().date()
    max_date = df_w["date"].max().date()

    start_d, end_d = st.sidebar.date_input(
        "Date range (Weather page)",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    mask = (df_w["date"].dt.date >= start_d) & (df_w["date"].dt.date <= end_d)
    df_w = df_w.loc[mask]

    rider_filter = "All"
    if "member_casual" in df_w.columns:
        rider_filter = st.sidebar.selectbox("Rider type (Weather page)", ["All", "member", "casual"])
        if rider_filter != "All":
            df_w = df_w[df_w["member_casual"] == rider_filter]

    if "ride_id" in df_w.columns:
        daily_weather = df_w.groupby("date").agg(
            trip_count=("ride_id", "count"),
            avg_temp=("avg_temp", "mean"),
            prcp=("PRCP", "mean"),
        ).reset_index().sort_values("date")
    else:
        daily_weather = df_w.groupby("date").agg(
            trip_count=("date", "size"),
            avg_temp=("avg_temp", "mean"),
            prcp=("PRCP", "mean"),
        ).reset_index().sort_values("date")

    col1, col2, col3 = st.columns(3)
    col1.metric("Trips (filtered)", f"{daily_weather['trip_count'].sum():,}")
    col2.metric("Avg temp", f"{daily_weather['avg_temp'].mean():.1f}")
    col3.metric("Avg precip", f"{daily_weather['prcp'].mean():.2f}")

    weather_var = st.radio(
        "Compare trips against:",
        ["Average Temperature", "Precipitation"],
        horizontal=True
    )

    st.subheader("Relationship Between Weather and Trip Volume")
    fig, ax = plt.subplots(figsize=(8, 5))
    if weather_var == "Average Temperature":
        ax.scatter(daily_weather["avg_temp"], daily_weather["trip_count"])
        ax.set_xlabel("Average Temperature")
        ax.set_ylabel("Daily Trips")
    else:
        ax.scatter(daily_weather["prcp"], daily_weather["trip_count"])
        ax.set_xlabel("Precipitation (PRCP)")
        ax.set_ylabel("Daily Trips")
    st_mpl(fig)

    st.subheader("Weather and Trips Over Time")
    fig2, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(daily_weather["date"], daily_weather["trip_count"])
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Daily Trips")

    ax2 = ax1.twinx()
    if weather_var == "Average Temperature":
        ax2.plot(daily_weather["date"], daily_weather["avg_temp"], linestyle="--")
        ax2.set_ylabel("Avg Temperature")
    else:
        ax2.plot(daily_weather["date"], daily_weather["prcp"], linestyle="--")
        ax2.set_ylabel("Precipitation")
    fig2.autofmt_xdate()
    st_mpl(fig2)

    with st.expander("Interpretation"):
        st.markdown(
            """
            Warmer temperatures generally align with higher ridership, while precipitation often reduces trips.
            This supports using forecasts to anticipate demand shifts and schedule rebalancing efficiently.
            """
        )

# --------------------------------------------------
# Stations & Routes Page
# --------------------------------------------------
elif page == "Stations & Routes":
    st.title("Stations & Routes")
    st.write("This page highlights popular stations and frequently used routes.")

    required_cols = ["start_station_name", "end_station_name"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        st.stop()

    df_sr = df.copy().dropna(subset=["start_station_name", "end_station_name"])

    rider_filter = "All"
    if "member_casual" in df_sr.columns:
        rider_filter = st.sidebar.selectbox("Rider type (Stations & Routes)", ["All", "member", "casual"])
        if rider_filter != "All":
            df_sr = df_sr[df_sr["member_casual"] == rider_filter]

    top_n_stations = st.sidebar.slider("Top stations", 5, 30, 10)
    top_n_routes = st.sidebar.slider("Top routes", 5, 30, 10)

    start_counts = df_sr["start_station_name"].value_counts().head(top_n_stations).sort_values()
    end_counts = df_sr["end_station_name"].value_counts().head(top_n_stations).sort_values()

    df_sr["route"] = df_sr["start_station_name"] + " → " + df_sr["end_station_name"]
    route_counts = df_sr["route"].value_counts().head(top_n_routes).sort_values()

    col1, col2, col3 = st.columns(3)
    col1.metric("Trips", f"{len(df_sr):,}")
    col2.metric("Unique start stations", f"{df_sr['start_station_name'].nunique():,}")
    col3.metric("Unique routes", f"{df_sr['route'].nunique():,}")

    st.subheader("Top Starting Stations")
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    ax1.barh(start_counts.index, start_counts.values)
    ax1.set_xlabel("Trips Started")
    st_mpl(fig1)

    st.subheader("Top Ending Stations")
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    ax2.barh(end_counts.index, end_counts.values)
    ax2.set_xlabel("Trips Ended")
    st_mpl(fig2)

    st.subheader("Most Frequent Routes (Start → End)")
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    ax3.barh(route_counts.index, route_counts.values)
    ax3.set_xlabel("Trips")
    st_mpl(fig3)

    with st.expander("Interpretation"):
        st.markdown(
            """
            High-frequency stations and routes reveal the system’s core demand hubs and travel corridors.
            These insights help prioritize rebalancing and capacity planning, especially during peak periods.
            """
        )

# --------------------------------------------------
# Kepler.gl Map Page
# --------------------------------------------------
elif page == "Kepler.gl Map":
    st.title("Kepler.gl Map")
    st.write("Interactive map of Citi Bike activity in New York City.")

    from keplergl import KeplerGl
    from streamlit_keplergl import keplergl_static

    config = {
        "version": "v1",
        "config": {
            "mapState": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "zoom": 10,
                "pitch": 0,
                "bearing": 0
            }
        }
    }

    map_1 = KeplerGl(height=650, config=config)
    map_1.add_data(data=df, name="Citi Bike Trips")

    keplergl_static(map_1, height=650)

    with st.expander("Interpretation"):
        st.markdown(
            """
            The Kepler map provides a spatial view of Citi Bike activity across New York City.
            Dense clusters indicate high-demand areas, often near transit hubs and commercial centers.
            These insights can guide rebalancing and station expansion decisions.
            """
        )

# --------------------------------------------------
# Popular Stations Page
# --------------------------------------------------
elif page == "Popular Stations":
    st.title("Most Popular Starting Stations")
    st.write("Stations with the highest number of trip starts in the dataset.")

    if "start_station_name" not in df.columns:
        st.error("Missing required column: start_station_name")
        st.stop()

    top_n = st.sidebar.slider("Number of stations to display", 5, 30, 10)

    top_stations = (
        df["start_station_name"]
        .dropna()
        .value_counts()
        .head(top_n)
        .sort_values(ascending=True)
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(top_stations.index, top_stations.values)
    ax.set_xlabel("Number of Trips Started")
    ax.set_ylabel("Starting Station")
    ax.set_title(f"Top {top_n} Starting Stations")
    st_mpl(fig)

    with st.expander("Interpretation"):
        st.markdown(
            f"""
            The top {top_n} starting stations represent key demand hubs where riders frequently begin trips.
            These stations are priority targets for rebalancing and dock capacity planning to prevent shortages
            during peak hours.
            """
        )

# --------------------------------------------------
# Station Balance (Supply Problem)
# --------------------------------------------------
elif page == "Station Balance (Supply Problem)":
    st.title("Station Balance (Supply Problem)")
    st.write("Stations that consistently lose or gain bikes (rebalancing needs).")

    required_cols = ["start_station_name", "end_station_name"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        st.stop()

    df_bal = df.copy().dropna(subset=["start_station_name", "end_station_name"])

    starts = df_bal["start_station_name"].value_counts().rename("starts")
    ends = df_bal["end_station_name"].value_counts().rename("ends")

    balance_df = (
        pd.concat([starts, ends], axis=1)
        .fillna(0)
        .reset_index()
        .rename(columns={"index": "station"})
    )
    balance_df["net_balance"] = balance_df["starts"] - balance_df["ends"]

    top_n = st.sidebar.slider("Number of stations to display (Balance)", 5, 30, 10)

    losing = balance_df.sort_values("net_balance").head(top_n)
    gaining = balance_df.sort_values("net_balance", ascending=False).head(top_n)

    col1, col2, col3 = st.columns(3)
    col1.metric("Stations analyzed", f"{balance_df.shape[0]:,}")
    col2.metric("Worst net loss", f"{losing['net_balance'].min():,.0f}")
    col3.metric("Worst net gain", f"{gaining['net_balance'].max():,.0f}")

    st.subheader("Stations Losing Bikes (Need Rebalancing IN)")
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    ax1.barh(losing["station"], losing["net_balance"])
    ax1.set_xlabel("Net Balance (Starts − Ends)")
    st_mpl(fig1)

    st.subheader("Stations Gaining Bikes (Need Rebalancing OUT)")
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.barh(gaining["station"], gaining["net_balance"])
    ax2.set_xlabel("Net Balance (Starts − Ends)")
    st_mpl(fig2)

    with st.expander("Interpretation"):
        st.markdown(
            """
            Stations with large negative values consistently lose bikes and require frequent rebalancing.
            Stations with large positive values accumulate bikes and risk dock congestion. These insights
            support rebalancing schedules and capacity planning.
            """
        )
