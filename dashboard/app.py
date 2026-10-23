
import os
from pathlib import Path

import mysql.connector
import pandas as pd
import streamlit as st


# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="Air Tracker | Flight Analytics",
    page_icon="✈️",
    layout="wide",
)

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"


# --------------------------------------------------
# 2. LOAD ENVIRONMENT VARIABLES
# --------------------------------------------------
def load_project_env():
    """Read .env without printing or exposing its contents."""
    if not ENV_FILE.exists():
        return

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key:
            os.environ.setdefault(key, value)


load_project_env()


# --------------------------------------------------
# 3. DATABASE CONNECTION
# --------------------------------------------------
def get_connection():
    password = os.getenv("MYSQL_PASSWORD")

    if not password:
        raise ValueError(
            "MYSQL_PASSWORD .env file mein nahi mila. "
            "Project root ki .env configuration check karein."
        )

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=password,
        database=os.getenv("MYSQL_DATABASE", "air_tracker"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        connection_timeout=10,
    )


def read_query(query, params=None):
    """Run a read-only query and return a DataFrame."""
    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        rows = cursor.fetchall()
        return pd.DataFrame(rows)
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


# --------------------------------------------------
# 4. LOAD FLIGHT AND AIRPORT DATA
# --------------------------------------------------
@st.cache_data(ttl=60)
def load_flights():
    query = """
        SELECT
            f.flight_id,
            f.flight_number,
            f.airline_code,
            f.aircraft_registration,
            f.origin_iata,
            f.destination_iata,
            f.scheduled_departure,
            f.actual_departure,
            f.scheduled_arrival,
            f.actual_arrival,
            f.status,
            origin.name AS origin_name,
            origin.city AS origin_city,
            destination.name AS destination_name,
            destination.city AS destination_city,
            aircraft.model AS aircraft_model
        FROM flight AS f
        LEFT JOIN airport AS origin
            ON UPPER(TRIM(f.origin_iata)) =
               UPPER(TRIM(origin.iata_code))
        LEFT JOIN airport AS destination
            ON UPPER(TRIM(f.destination_iata)) =
               UPPER(TRIM(destination.iata_code))
        LEFT JOIN aircraft
            ON UPPER(TRIM(f.aircraft_registration)) =
               UPPER(TRIM(aircraft.registration))
        ORDER BY f.flight_id DESC
    """
    return read_query(query)


@st.cache_data(ttl=60)
def load_airports():
    return read_query("""
        SELECT
            iata_code,
            name,
            city,
            country
        FROM airport
        ORDER BY name
    """)


@st.cache_data(ttl=60)
def load_aircraft():
    return read_query("""
        SELECT aircraft_id, registration, model, manufacturer
        FROM aircraft
        ORDER BY model
    """)


@st.cache_data(ttl=60)
def load_delays():
    query = """
        SELECT
            d.airport_iata,
            a.name AS airport_name,
            a.city,
            d.delay_date,
            d.flight_type,
            d.total_flight,
            d.delayed_flight,
            d.delay_index,
            d.median_delay_min,
            d.canceled_flight
        FROM airport_delays AS d
        LEFT JOIN airport AS a
            ON UPPER(TRIM(d.airport_iata)) =
               UPPER(TRIM(a.iata_code))
        ORDER BY d.delay_date DESC, d.airport_iata
    """
    return read_query(query)


# --------------------------------------------------
# 5. LOAD DATA SAFELY
# --------------------------------------------------
st.title("✈️ Air Tracker")
st.subheader("Flight Analytics Dashboard")
st.caption("Flight operations, airport performance and delay analysis")

try:
    flights = load_flights()
    airports = load_airports()
    aircraft = load_aircraft()
    delays = load_delays()
except Exception as error:
    st.error(
        "Database connection ya data loading mein problem aayi. "
        "MySQL service, .env configuration aur table names check karein."
    )
    st.caption(f"Technical detail: {type(error).__name__}: {error}")
    st.stop()


if flights.empty:
    st.warning("Flight table mein abhi koi record nahi hai.")
    st.stop()


# --------------------------------------------------
# 6. KPI CARDS
# --------------------------------------------------
total_records = len(flights)
unique_flights = flights[
    ["flight_number", "origin_iata", "destination_iata",
     "scheduled_departure"]
].drop_duplicates().shape[0]

col1, col2, col3, col4 = st.columns(4)

col1.metric("Flight Records", f"{total_records:,}")
col2.metric("Unique Flight Keys", f"{unique_flights:,}")
col3.metric("Airports", f"{len(airports):,}")
col4.metric("Aircraft", f"{len(aircraft):,}")

if total_records != unique_flights:
    st.info(
        f"Data quality note: {total_records - unique_flights:,} "
        "record(s) share an existing flight key. Records are not "
        "automatically deleted or hidden."
    )


# --------------------------------------------------
# 7. SIDEBAR FILTERS
# --------------------------------------------------
st.sidebar.header("🔎 Flight Filters")

search_text = st.sidebar.text_input(
    "Flight number or airline",
    placeholder="e.g. 6E 817 or 6E",
)

statuses = sorted(
    flights["status"].dropna().astype(str).unique().tolist()
)
selected_statuses = st.sidebar.multiselect(
    "Flight status",
    statuses,
    default=[],
)

origins = sorted(
    flights["origin_iata"].dropna().astype(str).unique().tolist()
)
selected_origins = st.sidebar.multiselect(
    "Origin airport",
    origins,
    default=[],
)

airlines = sorted(
    flights["airline_code"].dropna().astype(str).unique().tolist()
)
selected_airlines = st.sidebar.multiselect(
    "Airline code",
    airlines,
    default=[],
)

filtered = flights.copy()

if search_text.strip():
    term = search_text.strip()
    mask = (
        filtered["flight_number"].fillna("").astype(str)
        .str.contains(term, case=False, regex=False)
        |
        filtered["airline_code"].fillna("").astype(str)
        .str.contains(term, case=False, regex=False)
    )
    filtered = filtered[mask]

if selected_statuses:
    filtered = filtered[
        filtered["status"].astype(str).isin(selected_statuses)
    ]

if selected_origins:
    filtered = filtered[
        filtered["origin_iata"].astype(str).isin(selected_origins)
    ]

if selected_airlines:
    filtered = filtered[
        filtered["airline_code"].astype(str).isin(selected_airlines)
    ]

# Parse schedule values for date filtering and display.
if "scheduled_departure" in filtered.columns:
    filtered["departure_datetime"] = pd.to_datetime(
        filtered["scheduled_departure"],
        errors="coerce",
        utc=True,
        format="mixed",
    )
else:
    filtered["departure_datetime"] = pd.NaT

valid_dates = filtered["departure_datetime"].dropna()

if not valid_dates.empty:
    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()

    date_range = st.sidebar.date_input(
        "Scheduled departure date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_date, end_date = date_range
        parsed_dates = filtered["departure_datetime"].dt.date
        filtered = filtered[
            parsed_dates.notna()
            & (parsed_dates >= start_date)
            & (parsed_dates <= end_date)
        ]
else:
    st.sidebar.caption("No valid scheduled departure dates available.")


# --------------------------------------------------
# 8. DASHBOARD TABS
# --------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Flights",
    "🛫 Airport Analysis",
    "⏱️ Delay Analysis",
    "📊 Insights",
    "🧮 SQL Analysis"
])


# --------------------------------------------------
# TAB 1: FLIGHT SEARCH
# --------------------------------------------------
with tab1:
    st.subheader("Flight Search Results")
    st.write(f"Matching records: **{len(filtered):,}**")

    display_columns = [
        "flight_number",
        "airline_code",
        "aircraft_registration",
        "aircraft_model",
        "origin_iata",
        "origin_city",
        "destination_iata",
        "destination_city",
        "scheduled_departure",
        "scheduled_arrival",
        "status",
    ]

    available_columns = [
        col for col in display_columns if col in filtered.columns
    ]

    st.dataframe(
        filtered[available_columns],
        use_container_width=True,
        hide_index=True,
    )

    csv_data = filtered[available_columns].to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download filtered flights as CSV",
        data=csv_data,
        file_name="air_tracker_filtered_flights.csv",
        mime="text/csv",
    )


# --------------------------------------------------
# TAB 2: AIRPORT ANALYSIS
# --------------------------------------------------
with tab2:
    st.subheader("Airport Directory")

    airport_search = st.text_input(
        "Search airport by IATA, name or city",
        key="airport_search",
    )

    airport_view = airports.copy()

    if airport_search.strip():
        term = airport_search.strip()
        airport_mask = pd.Series(False, index=airport_view.index)

        for column in ["iata_code", "name", "city", "country"]:
            airport_mask |= (
                airport_view[column]
                .fillna("")
                .astype(str)
                .str.contains(term, case=False, regex=False)
            )

        airport_view = airport_view[airport_mask]

    st.dataframe(
        airport_view,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("Departures by Origin Airport")

    departure_counts = (
        flights["origin_iata"]
        .dropna()
        .value_counts()
        .rename_axis("Airport")
        .reset_index(name="Flight Records")
    )

    if not departure_counts.empty:
        st.bar_chart(
            departure_counts.head(15).set_index("Airport")
        )


# --------------------------------------------------
# TAB 3: AIRPORT DELAY ANALYSIS
# --------------------------------------------------
with tab3:
    st.subheader("Airport Delay Statistics")

    if delays.empty:
        st.warning("No airport delay statistics are available.")
    else:
        st.dataframe(
            delays,
            use_container_width=True,
            hide_index=True,
        )

        delay_values = pd.to_numeric(
            delays["delayed_flight"], errors="coerce"
        )

        if delay_values.notna().any():
            st.subheader("Delayed Flights by Airport")

            chart_data = delays.copy()
            chart_data["delayed_flight"] = pd.to_numeric(
                chart_data["delayed_flight"], errors="coerce"
            )
            chart_data = chart_data.dropna(
                subset=["delayed_flight"]
            )

            if not chart_data.empty:
                chart_data["airport_label"] = (
                    chart_data["airport_iata"].astype(str)
                    + " - "
                    + chart_data["flight_type"].astype(str)
                )

                st.bar_chart(
                    chart_data.set_index("airport_label")[
                        ["delayed_flight"]
                    ]
                )
        else:
            st.warning(
                "The delayed_flight field is NULL in the current "
                "database records. NULL means unavailable, not zero. "
                "Delayed-flight charts will appear after this field "
                "is populated with verified API data."
            )

        median_values = pd.to_numeric(
            delays["median_delay_min"], errors="coerce"
        )

        if median_values.notna().any():
            st.subheader("Median Delay (minutes)")

            median_chart = delays.copy()
            median_chart["median_delay_min"] = median_values
            median_chart = median_chart.dropna(
                subset=["median_delay_min"]
            )
            median_chart["airport_label"] = (
                median_chart["airport_iata"].astype(str)
                + " - "
                + median_chart["flight_type"].astype(str)
            )

            st.bar_chart(
                median_chart.set_index("airport_label")[
                    ["median_delay_min"]
                ]
            )


# --------------------------------------------------
# TAB 4: INSIGHTS
# --------------------------------------------------
with tab4:
    st.subheader("Flight Status Distribution")

    status_counts = (
        flights["status"]
        .fillna("Unknown")
        .astype(str)
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Records")
    )

    st.bar_chart(status_counts.set_index("Status"))

    left, right = st.columns(2)

    with left:
        st.subheader("Top 10 Destinations")

        destination_counts = (
            flights["destination_iata"]
            .dropna()
            .value_counts()
            .head(10)
            .rename_axis("Destination")
            .reset_index(name="Flight Records")
        )

        if not destination_counts.empty:
            st.bar_chart(
                destination_counts.set_index("Destination")
            )

    with right:
        st.subheader("Top 10 Aircraft Models")

        model_counts = (
            flights["aircraft_model"]
            .dropna()
            .value_counts()
            .head(10)
            .rename_axis("Aircraft Model")
            .reset_index(name="Flight Records")
        )

        if not model_counts.empty:
            st.bar_chart(
                model_counts.set_index("Aircraft Model")
            )

    st.caption(
        "Charts are based on the records currently stored in MySQL. "
        "Duplicate flight keys may affect record-based counts."
    )

with tab5:
    st.subheader("SQL Analysis")
    st.write("Run project SQL queries and view the results.")

    sql_queries = {
        "Total Flights per Aircraft Model": """
            SELECT a.model AS aircraft_model,
                   COUNT(f.flight_id) AS total_flights
            FROM aircraft a
            LEFT JOIN flight f
                ON a.registration = f.aircraft_registration
            GROUP BY a.model
            ORDER BY total_flights DESC
        """,
        "Top 3 Destination Airports": """
            SELECT a.iata_code AS airport_iata,
                   a.name AS airport_name,
                   COUNT(f.flight_id) AS total_arrivals
            FROM airport a
            JOIN flight f
                ON f.destination_iata = a.iata_code
            GROUP BY a.iata_code, a.name
            ORDER BY total_arrivals DESC
            LIMIT 3
        """,
        "Flight Status Counts by Airline": """
            SELECT airline_code,
                   LOWER(TRIM(status)) AS flight_status,
                   COUNT(*) AS total_flights
            FROM flight
            GROUP BY airline_code, LOWER(TRIM(status))
            ORDER BY airline_code, total_flights DESC
        """
    }

    selected_query = st.selectbox(
        "Select SQL Query",
        list(sql_queries.keys())
    )

    if st.button("Run SQL Query"):
        try:
            result_df = read_query(sql_queries[selected_query])
            st.dataframe(result_df, width="stretch")
            st.success(f"Query returned {len(result_df)} rows.")
        except Exception as e:
            st.error(f"Query failed: {e}")

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.divider()
st.caption(
    "Air Tracker | Flight Analytics — Python, Streamlit and MySQL"
)
