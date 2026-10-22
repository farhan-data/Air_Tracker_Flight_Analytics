import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Project ki .env file load karein
PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

API_KEY = os.getenv("RAPIDAPI_KEY")

if not API_KEY:
    raise ValueError("RAPIDAPI_KEY .env file mein nahi mili.")

# 15 airports ke IATA codes
airport_codes = [
    "AMD", "BLR", "BOM", "CCU", "COK",
    "DEL", "GOI", "HYD", "JAI", "LKO",
    "MAA", "PNQ", "TRV", "VNS", "VTZ"
]

headers = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "aerodatabox.p.rapidapi.com"
}

# Sabhi airports ka data ek JSON file mein save hoga
output_file = (
    Path(__file__).resolve().parent
    / "airport_delay_data.json"
)

all_airport_data = {}
failed_airports = []

for index, airport in enumerate(airport_codes):

    url = (
        f"https://aerodatabox.p.rapidapi.com/"
        f"airports/iata/{airport}/delays"
    )

    print(f"\nRequesting delay data for {airport}...")

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        print("HTTP status:", response.status_code)
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            print(f"Invalid response for {airport}")
            failed_airports.append(airport)
            continue

        all_airport_data[airport] = data

        print("Airport ICAO:", data.get("airportIcao"))

        print(
            "Departure information:",
            data.get("departuresDelayInformation")
        )

        print(
            "Arrival information:",
            data.get("arrivalsDelayInformation")
        )

    except (requests.exceptions.RequestException, ValueError) as error:
        print(f"Request failed for {airport}: {error}")
        failed_airports.append(airport)

    # API par bahut tezi se requests bhejne se bachein
    if index < len(airport_codes) - 1:
        time.sleep(1)

# Sabhi successful responses JSON file mein save karein
with open(output_file, "w", encoding="utf-8") as file:
    json.dump(
        {
            "airports": all_airport_data,
            "failed_airports": failed_airports
        },
        file,
        indent=4,
        ensure_ascii=False
    )

print("\n--- AIRPORT DELAY API SUMMARY ---")
print("Airports requested:", len(airport_codes))
print("Successful responses:", len(all_airport_data))
print("Failed airports:", failed_airports)
print("JSON data saved to:", output_file)

