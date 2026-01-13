import streamlit as st
import pandas as pd

# --------------------------------------------------
# App configuration
# --------------------------------------------------
st.set_page_config(
    page_title="NYC CitiBike Dashboard (2022)",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    iframe {
        width: 100% !important;
        height: 650px !important;
        min-height: 650px !important;
        margin-bottom: -140px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


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

    # Citi Bike station image (online source)
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
        - **Weather Impact**: Relationship between weather and ridership
        - **Stations & Routes**: Popular stations and trip pairs
        - **Kepler.gl Map**: Interactive spatial visualization
        """
    )

    st.info(
        "Data note: This dashboard uses a reproducible random sample (seed = 32) "
        "kept under 25 MB to ensure performance."
    )

# --------------------------------------------------
# Overview Page
# --------------------------------------------------
elif page == "Overview":
    st.title("Overview")

    st.write("Preview of the reduced Citi Bike dataset:")
    st.dataframe(df.head(20))

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
    st.write("This page will show daily, monthly, and seasonal trip patterns.")

    # --- Prepare time data ---
    if "started_at" not in df.columns:
        st.error("Missing required column: started_at")
        st.stop()

    df_time = df.copy()
    df_time["started_at"] = pd.to_datetime(df_time["started_at"], errors="coerce")
    df_time = df_time.dropna(subset=["started_at"])

    df_time["date"] = df_time["started_at"].dt.floor("D")
    df_time["month"] = df_time["started_at"].dt.month_name()
    df_time["hour"] = df_time["started_at"].dt.hour

    # --- Sidebar filters ---
    min_date = df_time["date"].min().date()
    max_date = df_time["date"].max().date()

    start_d, end_d = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    rider_filter = "All"
    if "member_casual" in df_time.columns:
        rider_filter = st.sidebar.selectbox("Rider type", ["All", "member", "casual"])

    # Apply filters
    mask = (df_time["date"].dt.date >= start_d) & (df_time["date"].dt.date <= end_d)
    df_time = df_time.loc[mask]

    if rider_filter != "All" and "member_casual" in df_time.columns:
        df_time = df_time[df_time["member_casual"] == rider_filter]

    # --- Aggregations ---
    daily = (
        df_time.groupby("date")
        .size()
        .reset_index(name="trip_count")
        .sort_values("date")
    )

    monthly = (
        df_time.groupby("month")
        .size()
        .reindex(
            ["January","February","March","April","May","June",
             "July","August","September","October","November","December"],
            fill_value=0
        )
    )

    hourly = (
        df_time.groupby("hour")
        .size()
        .reindex(range(24), fill_value=0)
    )

    # --- Metrics ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Trips (filtered)", f"{len(df_time):,}")
    col2.metric("Avg trips / day", f"{daily['trip_count'].mean():,.0f}" if len(daily) else "0")
    col3.metric("Peak hour", f"{hourly.idxmax():02d}:00" if hourly.sum() else "N/A")

    # --- Charts ---
    import matplotlib.pyplot as plt

    st.subheader("Daily Trip Volume")
    fig1, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(daily["date"], daily["trip_count"])
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Trips")
    fig1.autofmt_xdate()
    st.pyplot(fig1)

    st.subheader("Trips by Month")
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.bar(monthly.index, monthly.values)
    ax2.set_ylabel("Trips")
    ax2.set_xlabel("Month")
    plt.xticks(rotation=45)
    st.pyplot(fig2)

    st.subheader("Trips by Hour of Day")
    fig3, ax3 = plt.subplots(figsize=(10, 4))
    ax3.bar(hourly.index, hourly.values)
    ax3.set_xlabel("Hour of Day (0–23)")
    ax3.set_ylabel("Trips")
    st.pyplot(fig3)

      # Interpretation
    st.markdown(
        """
        **Interpretation**

        The daily trend highlights fluctuations in Citi Bike usage over time, with noticeable
        peaks that indicate periods of elevated demand. These peaks can increase pressure on
        bike availability at popular origin stations.

        Monthly patterns reveal seasonality, with higher usage during warmer months and lower
        demand in colder periods. The hourly distribution shows clear demand concentrations
        during specific times of day, which is critical for scheduling **rebalancing operations**
        and ensuring bikes and docks are available when riders need them most.
        """
    )

# --------------------------------------------------
# Weather Impact Page
# --------------------------------------------------
elif page == "Weather Impact":
    st.title("Weather Impact")
    st.write("This page will analyze how weather variables relate to trip volume.")

 # --- Validate required columns ---
    required_cols = ["started_at", "TMAX", "TMIN", "PRCP"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        st.stop()

    # --- Prepare data ---
    df_w = df.copy()
    df_w["started_at"] = pd.to_datetime(df_w["started_at"], errors="coerce")

    df_w["TMAX"] = pd.to_numeric(df_w["TMAX"], errors="coerce")
    df_w["TMIN"] = pd.to_numeric(df_w["TMIN"], errors="coerce")
    df_w["PRCP"] = pd.to_numeric(df_w["PRCP"], errors="coerce")

    df_w = df_w.dropna(subset=["started_at", "TMAX", "TMIN", "PRCP"])
    df_w["avg_temp"] = (df_w["TMAX"] + df_w["TMIN"]) / 2
    df_w["date"] = df_w["started_at"].dt.floor("D")

    # --- Sidebar filters ---
    min_date = df_w["date"].min().date()
    max_date = df_w["date"].max().date()

    start_d, end_d = st.sidebar.date_input(
        "Date range (Weather page)",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    rider_filter = "All"
    if "member_casual" in df_w.columns:
        rider_filter = st.sidebar.selectbox("Rider type (Weather page)", ["All", "member", "casual"])

    # Apply filters
    mask = (df_w["date"].dt.date >= start_d) & (df_w["date"].dt.date <= end_d)
    df_w = df_w.loc[mask]

    if rider_filter != "All" and "member_casual" in df_w.columns:
        df_w = df_w[df_w["member_casual"] == rider_filter]

    # --- Daily aggregation (trip count + weather) ---
    if "ride_id" in df_w.columns:
        daily_weather = (
            df_w.groupby("date")
            .agg(
                trip_count=("ride_id", "count"),
                avg_temp=("avg_temp", "mean"),
                prcp=("PRCP", "mean"),
            )
            .reset_index()
            .sort_values("date")
        )
    else:
        daily_weather = (
            df_w.groupby("date")
            .agg(
                trip_count=("date", "size"),
                avg_temp=("avg_temp", "mean"),
                prcp=("PRCP", "mean"),
            )
            .reset_index()
            .sort_values("date")
        )

    # --- Quick metrics ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Trips (filtered)", f"{daily_weather['trip_count'].sum():,}")
    col2.metric("Avg temp", f"{daily_weather['avg_temp'].mean():.1f}")
    col3.metric("Avg precip", f"{daily_weather['prcp'].mean():.2f}")

    # --- Choose weather variable to compare ---
    weather_var = st.radio(
        "Compare trips against:",
        ["Average Temperature", "Precipitation"],
        horizontal=True
    )

    import matplotlib.pyplot as plt

    # Scatter plot: trips vs selected weather variable
    st.subheader("Relationship Between Weather and Trip Volume")

    fig, ax = plt.subplots(figsize=(8, 5))
    if weather_var == "Average Temperature":
        ax.scatter(daily_weather["avg_temp"], daily_weather["trip_count"])
        ax.set_xlabel("Average Temperature (from TMAX/TMIN)")
        ax.set_ylabel("Daily Trips")
        ax.set_title("Trips vs Average Temperature")
    else:
        ax.scatter(daily_weather["prcp"], daily_weather["trip_count"])
        ax.set_xlabel("Precipitation (PRCP)")
        ax.set_ylabel("Daily Trips")
        ax.set_title("Trips vs Precipitation")

    st.pyplot(fig)

    # Line chart: trips + selected weather variable over time
    st.subheader("Weather and Trips Over Time")

    fig2, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(daily_weather["date"], daily_weather["trip_count"])
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Daily Trips")

    ax2 = ax1.twinx()
    if weather_var == "Average Temperature":
        ax2.plot(daily_weather["date"], daily_weather["avg_temp"], linestyle="--")
        ax2.set_ylabel("Average Temperature")
    else:
        ax2.plot(daily_weather["date"], daily_weather["prcp"], linestyle="--")
        ax2.set_ylabel("Precipitation (PRCP)")

    fig2.autofmt_xdate()
    st.pyplot(fig2)

       # Interpretation
    st.markdown(
        """
        **Interpretation**
        This page compares daily trip counts with weather conditions. Generally, warmer temperatures
        are associated with higher ridership, while precipitation tends to suppress demand on wetter days.
        These relationships are useful for Citi Bike supply planning: forecasts can help anticipate
        demand shifts and schedule rebalancing more effectively during high-demand periods.
        """
    )
    
# --------------------------------------------------
# Stations & Routes Page
# --------------------------------------------------
elif page == "Stations & Routes":
    st.title("Stations & Routes")
    st.write("This page will highlight popular stations and frequently used routes.")

    # --- Validate required columns ---
    required_cols = ["start_station_name", "end_station_name"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        st.stop()

    df_sr = df.copy()
    df_sr = df_sr.dropna(subset=["start_station_name", "end_station_name"])

    # Optional date filter
    if "started_at" in df_sr.columns:
        df_sr["started_at"] = pd.to_datetime(df_sr["started_at"], errors="coerce")
        df_sr = df_sr.dropna(subset=["started_at"])
        df_sr["date"] = df_sr["started_at"].dt.floor("D")

        min_date = df_sr["date"].min().date()
        max_date = df_sr["date"].max().date()

        start_d, end_d = st.sidebar.date_input(
            "Date range (Stations & Routes)",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        mask = (df_sr["date"].dt.date >= start_d) & (df_sr["date"].dt.date <= end_d)
        df_sr = df_sr.loc[mask]

    # Rider filter
    rider_filter = "All"
    if "member_casual" in df_sr.columns:
        rider_filter = st.sidebar.selectbox(
            "Rider type (Stations & Routes)",
            ["All", "member", "casual"]
        )
        if rider_filter != "All":
            df_sr = df_sr[df_sr["member_casual"] == rider_filter]

    # Controls
    top_n_stations = st.sidebar.slider("Top stations", 5, 30, 10)
    top_n_routes = st.sidebar.slider("Top routes", 5, 30, 10)

    # Aggregations
    start_counts = (
        df_sr["start_station_name"]
        .value_counts()
        .head(top_n_stations)
        .sort_values(ascending=True)
    )

    end_counts = (
        df_sr["end_station_name"]
        .value_counts()
        .head(top_n_stations)
        .sort_values(ascending=True)
    )

    df_sr["route"] = df_sr["start_station_name"] + " → " + df_sr["end_station_name"]

    route_counts = (
        df_sr["route"]
        .value_counts()
        .head(top_n_routes)
        .sort_values(ascending=True)
    )

    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Trips", f"{len(df_sr):,}")
    col2.metric("Unique start stations", f"{df_sr['start_station_name'].nunique():,}")
    col3.metric("Unique routes", f"{df_sr['route'].nunique():,}")

    # Plots
    import matplotlib.pyplot as plt

    st.subheader("Top Starting Stations")
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    ax1.barh(start_counts.index, start_counts.values)
    ax1.set_xlabel("Trips Started")
    st.pyplot(fig1)

    st.subheader("Top Ending Stations")
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    ax2.barh(end_counts.index, end_counts.values)
    ax2.set_xlabel("Trips Ended")
    st.pyplot(fig2)

    st.subheader("Most Frequent Routes (Start → End)")
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    ax3.barh(route_counts.index, route_counts.values)
    ax3.set_xlabel("Trips")
    st.pyplot(fig3)

       # Interpretation
    st.markdown(
        """
        **Interpretation**

        The most popular starting and ending stations represent key demand hubs in the Citi Bike system.
        These locations are most vulnerable to bike shortages or dock congestion during peak periods.

        Frequently used Start → End routes highlight common travel corridors that drive system imbalance.
        Understanding these flows supports targeted rebalancing, capacity planning, and potential station
        expansion decisions.
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

    # --- Create a Kepler map with an explicit NYC view ---
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

    # If you have station coordinates, these are the columns Kepler will use:
    # start_lat/start_lng (and/or end_lat/end_lng)
    map_1.add_data(data=df, name="Citi Bike Trips")

    # Make it large
    keplergl_static(map_1, height=650)

    st.markdown(
        """
        **Interpretation**

        The Kepler.gl map provides a spatial view of Citi Bike activity across New York City.
        Dense clusters indicate high-demand areas (often near transit hubs and commercial/residential centers).
        These spatial patterns can guide rebalancing, dock capacity planning, and potential station expansion.
        """
    )


#---------------------------------------------------
#Dual-Axis
#---------------------------------------------------

elif page == "Dual-Axis: Trips vs Temperature":
    st.title("Trips vs Temperature Over Time")

    st.write(
        "This chart compares daily Citi Bike trip volume with average daily temperature "
        "to highlight seasonal and weather-related patterns in ridership."
    )

    # --- Validate required columns ---
    required_cols = ["started_at", "TMAX", "TMIN"]
    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        st.stop()

    # --- Prepare data ---
    df_time = df.copy()

    # Convert to datetime
    df_time["started_at"] = pd.to_datetime(df_time["started_at"], errors="coerce")

    # Convert temps to numeric
    df_time["TMAX"] = pd.to_numeric(df_time["TMAX"], errors="coerce")
    df_time["TMIN"] = pd.to_numeric(df_time["TMIN"], errors="coerce")

    # Drop rows with missing values
    df_time = df_time.dropna(subset=["started_at", "TMAX", "TMIN"])

    # Create average temperature
    df_time["avg_temp"] = (df_time["TMAX"] + df_time["TMIN"]) / 2

    # Create daily date
    df_time["date"] = df_time["started_at"].dt.floor("D")

    # Aggregate by day
    daily_summary = (
        df_time.groupby("date")
        .agg(
            trip_count=("ride_id", "count"),
            avg_temp=("avg_temp", "mean")
        )
        .reset_index()
        .sort_values("date")
    )

    # --- Plot dual-axis chart ---
    import matplotlib.pyplot as plt

    fig, ax1 = plt.subplots(figsize=(10, 5))

    ax1.plot(
        daily_summary["date"],
        daily_summary["trip_count"],
        label="Daily Trips"
    )
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Number of Trips")

    ax2 = ax1.twinx()
    ax2.plot(
        daily_summary["date"],
        daily_summary["avg_temp"],
        linestyle="--",
        label="Average Temperature"
    )
    ax2.set_ylabel("Average Temperature")

    fig.autofmt_xdate()
    st.pyplot(fig)

      # Interpretation
    st.markdown(
        """
        **Interpretation**

        The dual-axis line chart illustrates a clear relationship between temperature and
        Citi Bike usage over time. As average daily temperatures increase, trip volume
        also rises, indicating stronger ridership during warmer months. In contrast,
        colder periods correspond with reduced bike usage.

        This relationship suggests that temperature is a key driver of Citi Bike demand
        in New York City and should be considered when planning seasonal operations,
        bike availability, and promotional strategies.
        """
    )



#----------------------------------------------------
#Popular Stations
#----------------------------------------------------
elif page == "Popular Stations":
    st.title("Most Popular Starting Stations")

    st.write(
        "This bar chart shows the stations with the highest number of trip starts in the dataset."
    )

    # --- Compute top stations ---
    top_n = st.sidebar.slider("Number of stations to display", 5, 30, 10)

    top_stations = (
        df["start_station_name"]
        .dropna()
        .value_counts()
        .head(top_n)
        .sort_values(ascending=True)
    )

    # --- Plot bar chart (horizontal) ---
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(top_stations.index, top_stations.values)

    ax.set_xlabel("Number of Trips Started")
    ax.set_ylabel("Starting Station")
    ax.set_title(f"Top {top_n} Starting Stations")

    st.pyplot(fig)

       # Interpretation
    st.markdown(
        """
        **Interpretation**

        The chart highlights the top **{top_n} starting stations** by trip count, showing where
        Citi Bike demand is most concentrated. Stations at the top of the list represent key
        demand hubs where riders frequently begin trips, often located near major transit
        connections, employment centers, universities, or high-traffic neighborhoods.

        From a strategy perspective, these stations are important for bike rebalancing and
        capacity planning. Ensuring that docks at high-demand stations have enough available
        bikes during peak periods can improve customer experience and reduce lost rides.
        """
    )



# --------------------------------------------------
# Station Balance (Supply Problem)
# --------------------------------------------------
elif page == "Station Balance (Supply Problem)":
    st.title("Station Balance (Supply Problem)")
    st.write(
        "This page identifies stations that consistently lose or gain bikes, "
        "highlighting where rebalancing is most critical."
    )

    # --- Validate required columns ---
    required_cols = ["start_station_name", "end_station_name"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        st.stop()

    df_bal = df.copy()
    df_bal = df_bal.dropna(subset=["start_station_name", "end_station_name"])

    # --- Optional date filter ---
    if "started_at" in df_bal.columns:
        df_bal["started_at"] = pd.to_datetime(df_bal["started_at"], errors="coerce")
        df_bal = df_bal.dropna(subset=["started_at"])
        df_bal["date"] = df_bal["started_at"].dt.floor("D")

        min_date = df_bal["date"].min().date()
        max_date = df_bal["date"].max().date()

        start_d, end_d = st.sidebar.date_input(
            "Date range (Balance)",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        mask = (
            (df_bal["date"].dt.date >= start_d)
            & (df_bal["date"].dt.date <= end_d)
        )
        df_bal = df_bal.loc[mask]

    # --- Compute station balance ---
    starts = df_bal["start_station_name"].value_counts().rename("starts")
    ends = df_bal["end_station_name"].value_counts().rename("ends")

    balance_df = (
        pd.concat([starts, ends], axis=1)
        .fillna(0)
        .reset_index()
        .rename(columns={"index": "station"})
    )

    balance_df["net_balance"] = balance_df["starts"] - balance_df["ends"]

    # --- Controls ---
    top_n = st.sidebar.slider("Number of stations to display", 5, 30, 10)

    losing = balance_df.sort_values("net_balance").head(top_n)
    gaining = balance_df.sort_values("net_balance", ascending=False).head(top_n)

    # --- Metrics ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Stations analyzed", f"{balance_df.shape[0]:,}")
    col2.metric("Worst net loss", f"{losing['net_balance'].min():,.0f}")
    col3.metric("Worst net gain", f"{gaining['net_balance'].max():,.0f}")

    import matplotlib.pyplot as plt

    # --- Plot: Losing bikes ---
    st.subheader("Stations Losing Bikes (Need Rebalancing IN)")
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    ax1.barh(losing["station"], losing["net_balance"])
    ax1.set_xlabel("Net Balance (Starts − Ends)")
    ax1.set_ylabel("Station")
    st.pyplot(fig1)

    # --- Plot: Gaining bikes ---
    st.subheader("Stations Gaining Bikes (Need Rebalancing OUT)")
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.barh(gaining["station"], gaining["net_balance"])
    ax2.set_xlabel("Net Balance (Starts − Ends)")
    ax2.set_ylabel("Station")
    st.pyplot(fig2)

    # Interpretation
    st.markdown(
        """
        **Interpretation**

        Net station balance highlights where the Citi Bike system becomes imbalanced.
        Stations with large negative values consistently lose bikes and require frequent
        rebalancing, while stations with large positive values accumulate bikes and risk
        dock congestion.

        These insights directly support supply-side decisions such as rebalancing schedules,
        dock capacity planning, and station expansion.
        """
    )
