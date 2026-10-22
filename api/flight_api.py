import json
import os
import json
from pathlib import Path
from datetime import datetime

import mysql.connector
from dotenv import load_dotenv


# ============================================================
# 1. PROJECT PATHS AND CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
JSON_FILE = Path(__file__).resolve().parent / "flight_data.json"
ENV_FILE = PROJECT_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)

FIDS_AIRPORT = "BLR"


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def clean_text(value):
    """Convert a value to clean text or None."""
    if value is None:
        return None

    value = str(value).strip()

    if not value or value.lower() in {"none", "null", "n/a"}:
        return None

    return value


def parse_datetime(value):
    """Convert an ISO datetime string into a MySQL-compatible datetime."""
    value = clean_text(value)

    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

        # Keep the displayed local clock time from the API.
        # MySQL DATETIME does not store timezone information.
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)

        return parsed

    except (ValueError, TypeError):
        return None


def get_local_time(data):
    """Read a nested local-time value from the API JSON."""
    if not isinstance(data, dict):
        return None

    scheduled_time = data.get("scheduledTime")

    if isinstance(scheduled_time, dict):
        local_time = scheduled_time.get("local")
        if local_time:
            return parse_datetime(local_time)

    return None


def get_runway_time(data):
    """Read runwayTime.local without using revisedTime as actual time."""
    if not isinstance(data, dict):
        return None

    runway_time = data.get("runwayTime")

    if isinstance(runway_time, dict):
        return parse_datetime(runway_time.get("local"))

    return None


def get_airport_code(data):
    """Extract an airport IATA code from a nested airport object."""
    if not isinstance(data, dict):
        return None

    return clean_text(data.get("iata"))


def normalize_key_text(value):
    """Normalize text used for duplicate checking."""
    value = clean_text(value)
    return value.upper() if value else None


def make_flight_key(number, origin, destination, scheduled):
    """Build a key to identify an existing flight."""
    return (
        normalize_key_text(number),
        normalize_key_text(origin),
        normalize_key_text(destination),
        scheduled,
    )


# ============================================================
# 3. LOAD FLIGHT JSON
# ============================================================

def load_flight_data():
    if not JSON_FILE.exists():
        raise FileNotFoundError(
            f"Flight JSON file not found: {JSON_FILE}"
        )

    with open(JSON_FILE, "r", encoding="utf-8") as file:
        flight_data = json.load(file)

    if not isinstance(flight_data, dict):
        raise ValueError("flight_data.json must contain a JSON object.")

    departures = flight_data.get("departures", [])
    arrivals = flight_data.get("arrivals", [])

    if not isinstance(departures, list):
        departures = []

    if not isinstance(arrivals, list):
        arrivals = []

    return {
        "departures": departures,
        "arrivals": arrivals,
    }


# ============================================================
# 4. MAP JSON DATA INTO DATABASE FIELDS
# ============================================================


def map_flights(flight_data):
    mapped_flights = []
    FIDS_AIRPORT = "BLR"

    for section in ("departures", "arrivals"):
        for record in flight_data.get(section, []):
            departure = record.get("departure") or {}
            arrival = record.get("arrival") or {}
            aircraft = record.get("aircraft") or {}
            airline = record.get("airline") or {}

            if section == "departures":
                origin = FIDS_AIRPORT
                destination = get_airport_code(
                    arrival.get("airport") or {}
                )
                flight_type = "Departure"
            else:
                origin = get_airport_code(
                    departure.get("airport") or {}
                )
                destination = FIDS_AIRPORT
                flight_type = "Arrival"

            mapped_flights.append({
                "flight_number": record.get("number"),
                "aircraft_registration": aircraft.get("reg"),
                "origin_iata": origin,
                "destination_iata": destination,
                "scheduled_departure": get_local_time(departure),
                "scheduled_arrival": get_local_time(arrival),
                "actual_departure": get_runway_time(departure),
                "actual_arrival": get_runway_time(arrival),
                "status": record.get("status"),
                "airline_code": airline.get("iata"),
                "flight_type": flight_type,
            })

    return mapped_flights


# ============================================================
# 5. CONNECT TO MYSQL
# ============================================================

def connect_mysql():
    password = os.getenv("MYSQL_PASSWORD")

    if password is None:
        raise ValueError(
            "MYSQL_PASSWORD .env file mein nahi mila. "
            "Project root ke .env file ko check karein."
        )

    connection = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=password,
        database=os.getenv("MYSQL_DATABASE", "air_tracker"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
    )

    return connection


# ============================================================
# 6. SAVE FLIGHTS INTO MYSQL
# ============================================================

def save_flights(mapped_flights):
    connection = None
    cursor = None

    inserted = 0
    skipped = 0
    invalid = 0

    try:
        connection = connect_mysql()
        cursor = connection.cursor()

        # Fetch existing flights for duplicate checking.
        cursor.execute("""
            SELECT
                flight_number,
                origin_iata,
                destination_iata,
                scheduled_departure
            FROM flight
        """)

        existing_flights = {
            make_flight_key(number, origin, destination, scheduled)
            for number, origin, destination, scheduled
            in cursor.fetchall()
        }

        insert_query = """
            INSERT INTO flight (
                flight_number,
                aircraft_registration,
                origin_iata,
                destination_iata,
                scheduled_departure,
                actual_departure,
                scheduled_arrival,
                actual_arrival,
                status,
                airline_code
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        for flight in mapped_flights:
            number = flight["flight_number"]
            origin = flight["origin_iata"]
            destination = flight["destination_iata"]
            scheduled = flight["scheduled_departure"]

            # Required fields must be present.
            if not number or not origin or not destination or not scheduled:
                invalid += 1
                continue

            flight_key = make_flight_key(
                number,
                origin,
                destination,
                scheduled,
            )

            # Skip duplicate flights.
            if flight_key in existing_flights:
                skipped += 1
                continue

            values = (
                number,
                flight["aircraft_registration"],
                origin,
                destination,
                scheduled,
                flight["actual_departure"],
                flight["scheduled_arrival"],
                flight["actual_arrival"],
                flight["status"],
                flight["airline_code"],
            )

            cursor.execute(insert_query, values)

            existing_flights.add(flight_key)
            inserted += 1

        connection.commit()

        print("\n========== FLIGHT DATABASE SUMMARY ==========")
        print(f"Total mapped flights : {len(mapped_flights)}")
        print(f"New flights inserted : {inserted}")
        print(f"Duplicate flights    : {skipped}")
        print(f"Invalid flights      : {invalid}")
        print("Database transaction : COMMITTED")
        print("==============================================")

    except Exception:
        if connection is not None:
            connection.rollback()

        print("Flight insert failed. Database changes rolled back.")
        raise

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()

    return inserted, skipped, invalid


# ============================================================
# 7. PRINT API DATA SUMMARY
# ============================================================

def print_status_summary(flight_data):
    departures = flight_data.get("departures", [])
    arrivals = flight_data.get("arrivals", [])

    print("\n========== API DATA SUMMARY ==========")
    print(f"Airport              : {FIDS_AIRPORT}")
    print(f"Departure records    : {len(departures)}")
    print(f"Arrival records      : {len(arrivals)}")
    print(f"Total API records    : {len(departures) + len(arrivals)}")
    print("======================================\n")


# ============================================================
# 8. MAIN FUNCTION
# ============================================================

def main():
    print("\nStarting Air Tracker Flight Analytics...")

    try:
        flight_data = load_flight_data()
        print_status_summary(flight_data)

        mapped_flights = map_flights(flight_data)

        # Show records that are missing required fields.
        print("\n========== INVALID FLIGHT DETAILS ==========")
        required_fields = (
            "flight_number",
            "origin_iata",
            "destination_iata",
            "scheduled_departure",
        )

        invalid_details_count = 0

        for flight in mapped_flights:
            missing_fields = [
                field for field in required_fields
                if not flight.get(field)
            ]

            if missing_fields:
                invalid_details_count += 1
                print(
                    f"Flight: {flight.get('flight_number')} | "
                    f"Missing: {', '.join(missing_fields)} | "
                    f"Type: {flight.get('flight_type')}"
                )

        if invalid_details_count == 0:
            print("No flights have missing required fields.")

        print("\n========== DEBUG: FIRST 3 FLIGHTS ==========")
        for flight in mapped_flights[:3]:
            print(flight)

        print("\n========== MISSING FIELD COUNTS ==========")
        for field in required_fields:
            missing_count = sum(
                1 for flight in mapped_flights
                if not flight.get(field)
            )
            print(
                f"{field}: {missing_count} missing "
                f"out of {len(mapped_flights)}"
            )

        print(f"Mapped flight records: {len(mapped_flights)}")

        save_flights(mapped_flights)

        print("\nFlight data processing completed.")

    except Exception as error:
        print(f"\nERROR: {error}")
        raise

# ============================================================
# 9. RUN SCRIPT
# ============================================================

if __name__ == "__main__":
    main()

