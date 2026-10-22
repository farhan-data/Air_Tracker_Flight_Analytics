import json
import os
import mysql.connector
from pathlib import Path
from dotenv import load_dotenv

# Project ki .env file load karein
PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

# Saved JSON file padhein
JSON_FILE = Path(__file__).resolve().parent / "airport_delay_data.json"

with open(JSON_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

# New JSON format se successful airports nikalein
airports_data = data.get("airports", {})

if not airports_data:
    raise ValueError(
        "JSON file mein successful airport data nahi mila."
    )

# MySQL database se connect karein
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password=os.getenv("MYSQL_PASSWORD"),
    database="air_tracker"
)

cursor = connection.cursor()

inserted_count = 0
skipped_count = 0

try:
    # Har successful airport ko process karein
    for airport_iata, airport_data in airports_data.items():

        # Delay report ki date nikalein
        date_info = airport_data.get("from", {})
        date_text = date_info.get("local") or date_info.get("utc")

        if not date_text:
            print(f"{airport_iata}: date nahi mili, skipped.")
            skipped_count += 2
            continue

        delay_date = date_text[:10]

        # Departure aur Arrival dono process karein
        for flight_type, key in [
            ("Departure", "departuresDelayInformation"),
            ("Arrival", "arrivalsDelayInformation")
        ]:
            info = airport_data.get(key) or {}

            if not info:
                print(
                    f"{airport_iata} {flight_type}: "
                    "delay information nahi mili, skipped."
                )
                skipped_count += 1
                continue

            # Median delay ko minutes mein convert karein
            median_delay = info.get("medianDelay")
            median_delay_min = None

            if median_delay:
                try:
                    hours, minutes, seconds = map(
                        int, median_delay.split(":")
                    )
                    median_delay_min = hours * 60 + minutes
                except (ValueError, AttributeError):
                    print(
                        f"{airport_iata} {flight_type}: "
                        f"invalid medianDelay: {median_delay}"
                    )

            # Duplicate record check karein
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM airport_delays
                WHERE airport_iata = %s
                  AND delay_date = %s
                  AND flight_type = %s
                """,
                (airport_iata, delay_date, flight_type)
            )

            exists = cursor.fetchone()[0]

            if exists:
                print(
                    f"{airport_iata} {flight_type}: "
                    "record already exists, skipped."
                )
                skipped_count += 1
                continue

            # Database mein record insert karein
            cursor.execute(
                """
                INSERT INTO airport_delays
                (
                    airport_iata,
                    delay_date,
                    total_flight,
                    delayed_flight,
                    delay_index,
                    median_delay_min,
                    canceled_flight,
                    flight_type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    airport_iata,
                    delay_date,
                    info.get("numTotal"),
                    None,
                    info.get("delayIndex"),
                    median_delay_min,
                    info.get("numCancelled"),
                    flight_type
                )
            )

            inserted_count += 1
            print(
                f"{airport_iata} {flight_type}: record inserted."
            )

    connection.commit()

except Exception:
    connection.rollback()
    raise

finally:
    cursor.close()
    connection.close()

print("\n--- AIRPORT DELAY INSERT SUMMARY ---")
print("Successful airports in JSON:", len(airports_data))
print("Records inserted:", inserted_count)
print("Records skipped:", skipped_count)
print("Airport delay data processing complete.")
