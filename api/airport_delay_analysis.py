
import os
import mysql.connector
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Project ki .env file load karein
PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

# MySQL database se connect karein
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password=os.getenv("MYSQL_PASSWORD"),
    database="air_tracker"
)

try:
    # Database se airport delay records padhein
    query = """
        SELECT
            airport_iata,
            delay_date,
            flight_type,
            total_flight,
            delayed_flight,
            delay_index,
            median_delay_min,
            canceled_flight
        FROM airport_delays
        ORDER BY delay_date, airport_iata, flight_type
    """

    df = pd.read_sql(query, connection)

    if df.empty:
        print("Airport delay table mein koi data nahi mila.")
    else:
        # Numeric columns ko numeric format mein rakhein
        numeric_columns = [
            "total_flight",
            "delayed_flight",
            "delay_index",
            "median_delay_min",
            "canceled_flight"
        ]

        for column in numeric_columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        # Report 1: Airport aur date ke hisaab se summary
        summary = (
            df.groupby(["delay_date", "airport_iata"], as_index=False)
            .agg(
                total_flights=("total_flight", "sum"),
                canceled_flights=("canceled_flight", "sum"),
                available_median_delay_min=("median_delay_min", "mean")
            )
        )

        # Cancellation percentage calculate karein
        summary["cancellation_percentage"] = (
            summary["canceled_flights"]
            .div(summary["total_flights"].replace(0, pd.NA))
            .mul(100)
            .round(2)
        )

        summary["available_median_delay_min"] = (
            summary["available_median_delay_min"].round(2)
        )

        print("\n=== AIRPORT DELAY ANALYSIS ===")
        print("\n1. Date-wise airport summary:\n")
        print(summary.to_string(index=False))
        output_file = PROJECT_DIR / "airport_delay_summary.csv"
        summary.to_csv(output_file, index=False)
        print(f"\nReport saved to: {output_file}")

        # Report 2: Flight type ke hisaab se summary
        flight_summary = (
            df.groupby(["delay_date", "flight_type"], as_index=False)
            .agg(
                total_flights=("total_flight", "sum"),
                canceled_flights=("canceled_flight", "sum"),
                available_median_delay_min=("median_delay_min", "mean")
            )
        )

        print("\n2. Arrival vs Departure summary:\n")
        print(flight_summary.to_string(index=False))

        # Report 3: Delayed-flight count ki availability
        known_delayed = df["delayed_flight"].notna().sum()
        total_records = len(df)

        print("\n3. Delayed-flight data availability:")
        print(f"Total records: {total_records}")
        print(f"Records with delayed-flight count: {known_delayed}")
        print(f"Records without delayed-flight count: {total_records - known_delayed}")

        print(
            "\nNote: Median delay sirf available values par based hai. "
            "Yeh sabhi flights ka average delay nahi hai."
        )

finally:
    connection.close()
