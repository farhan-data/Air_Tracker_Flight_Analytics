
import os
from pathlib import Path

import mysql.connector
import requests
from dotenv import load_dotenv


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

AIRCRAFT_API_URL = "https://api.adsbdb.com/v0/aircraft"

AIRCRAFT_FIELDS = (
    "model",
    "manufacturer",
    "icao_type_code",
    "owner",
)


# ============================================================
# 2. FETCH AIRCRAFT FROM API
# ============================================================

def fetch_aircraft(registration):
    """Fetch aircraft data and map it to database columns."""

    registration = str(registration or "").strip().upper()

    if not registration:
        print("Skipped: empty registration.")
        return None

    try:
        response = requests.get(
            f"{AIRCRAFT_API_URL}/{registration}",
            timeout=15,
        )

        if response.status_code == 404:
            print(f"Aircraft not found in API: {registration}")
            return None

        response.raise_for_status()
        payload = response.json()

        if not isinstance(payload, dict):
            print("Invalid API response: expected a JSON object.")
            return None

        response_data = payload.get("response")

        if not isinstance(response_data, dict):
            print(f"Invalid API response for {registration}.")
            return None

        aircraft = response_data.get("aircraft")

        if not isinstance(aircraft, dict):
            print(f"Aircraft data missing for {registration}.")
            return None

        api_registration = str(
            aircraft.get("registration") or ""
        ).strip().upper()

        # Do not accept a different aircraft's response.
        if api_registration != registration:
            print(
                f"Registration mismatch: requested {registration}, "
                f"received {api_registration or 'missing registration'}."
            )
            return None

        result = {
            "registration": api_registration,
            "model": aircraft.get("type"),
            "manufacturer": aircraft.get("manufacturer"),
            "icao_type_code": aircraft.get("icao_type"),
            "owner": aircraft.get("registered_owner"),
        }

        # Normalize empty values to None.
        for field in AIRCRAFT_FIELDS:
            value = result[field]

            if value is not None:
                value = str(value).strip()
                result[field] = value or None

        if not any(result[field] for field in AIRCRAFT_FIELDS):
            print(f"No usable aircraft details for {registration}.")
            return None

        return result

    except requests.RequestException as error:
        print(f"API request failed for {registration}: {error}")
        return None

    except (ValueError, TypeError, AttributeError) as error:
        print(f"Invalid API response for {registration}: {error}")
        return None


# ============================================================
# 3. MYSQL CONNECTION
# ============================================================

def connect_mysql():
    """Connect to the project's MySQL database."""

    password = os.getenv("MYSQL_PASSWORD")

    if password is None:
        raise ValueError(
            "MYSQL_PASSWORD .env file mein nahi mila."
        )

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=password,
        database=os.getenv("MYSQL_DATABASE", "air_tracker"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
    )


# ============================================================
# 4. INSERT OR FILL EMPTY AIRCRAFT FIELDS
# ============================================================

def save_aircraft(aircraft_data):
    """
    Insert a new aircraft or fill only empty existing fields.

    Existing non-empty fields are never overwritten.
    Returns True on success and False when data is skipped.
    """

    if not isinstance(aircraft_data, dict):
        print("Skipped: aircraft data must be a dictionary.")
        return False

    registration = str(
        aircraft_data.get("registration") or ""
    ).strip().upper()

    if not registration:
        print("Skipped: missing registration.")
        return False

    values = {}

    for field in AIRCRAFT_FIELDS:
        value = aircraft_data.get(field)

        if value is None:
            values[field] = None
        else:
            value = str(value).strip()
            values[field] = value or None

    # Do not insert a registration with no useful aircraft details.
    if not any(values.values()):
        print(f"Skipped: no usable details for {registration}.")
        return False

    connection = None
    cursor = None

    try:
        connection = connect_mysql()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT model, manufacturer, icao_type_code, owner
            FROM aircraft
            WHERE registration = %s
            """,
            (registration,),
        )

        existing = cursor.fetchone()

        if existing is None:
            cursor.execute(
                """
                INSERT INTO aircraft (
                    registration,
                    model,
                    manufacturer,
                    icao_type_code,
                    owner
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    registration,
                    values["model"],
                    values["manufacturer"],
                    values["icao_type_code"],
                    values["owner"],
                ),
            )

            action = "inserted"

        else:
            updates = []
            parameters = []

            for field, old_value in zip(AIRCRAFT_FIELDS, existing):
                new_value = values[field]

                old_is_empty = (
                    old_value is None
                    or not str(old_value).strip()
                )

                if old_is_empty and new_value is not None:
                    updates.append(f"{field} = %s")
                    parameters.append(new_value)

            if updates:
                parameters.append(registration)

                cursor.execute(
                    f"""
                    UPDATE aircraft
                    SET {", ".join(updates)}
                    WHERE registration = %s
                    """,
                    tuple(parameters),
                )

                action = "filled empty fields"
            else:
                action = "unchanged"

        connection.commit()
        print(f"{registration}: {action}")
        return True

    except mysql.connector.Error:
        if connection is not None and connection.is_connected():
            connection.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# ============================================================
# 5. MANUAL FETCH TEST
# ============================================================

if __name__ == "__main__":
    # This test fetches data only; it does NOT write to MySQL.
    test_registration = "N547TW"
    result = fetch_aircraft(test_registration)

    if result:
        print("Aircraft data fetched successfully:")

        for key, value in result.items():
            print(f"{key}: {value}")
    else:
        print("No aircraft data returned.")
