import json
from pathlib import Path
from datetime import datetime

# Project ke saved JSON file ka path
API_DIR = Path(__file__).resolve().parent
JSON_FILE = API_DIR / "flight_data.json"

# Saved flight data load karein
with open(JSON_FILE, "r", encoding="utf-8") as file:
    flight_data = json.load(file)

print("--- SAVED FLIGHT DELAY CHECK ---")

for section in ("departures", "arrivals"):
    records = flight_data.get(section, [])
    revised_count = 0
    actual_count = 0
    scheduled_count = 0

    for record in records:
        for field in ("departure", "arrival"):
            details = record.get(field) or {}

            if details.get("scheduledTime"):
                scheduled_count += 1

            if details.get("revisedTime"):
                revised_count += 1

            if details.get("actualTime"):
                actual_count += 1

    print(f"\n{section.title()}: {len(records)} records")
    print("Scheduled time fields:", scheduled_count)
    print("Revised time fields:", revised_count)
    print("Actual time fields:", actual_count)


print("\n--- REVISED TIME DELAY CALCULATION ---")

for section in ("departures", "arrivals"):
    records = flight_data.get(section, [])
    delays = []

    for record in records:
        event = "departure" if section == "departures" else "arrival"
        details = record.get(event) or {}

        scheduled = details.get("scheduledTime", {}).get("local")
        revised = details.get("revisedTime", {}).get("local")

        if scheduled and revised:
            try:
                scheduled_dt = datetime.fromisoformat(scheduled)
                revised_dt = datetime.fromisoformat(revised)

                delay_minutes = round(
                    (revised_dt - scheduled_dt).total_seconds() / 60
                )
                delays.append(delay_minutes)

            except (ValueError, TypeError):
                continue

    delayed = [minutes for minutes in delays if minutes > 0]

    print(f"\n{section.title()}:")
    print("Flights with both times:", len(delays))
    print("Flights revised later than scheduled:", len(delayed))

    if delays:
        print("Average difference (minutes):", round(sum(delays) / len(delays), 2))
        print("Median difference (minutes):", sorted(delays)[len(delays) // 2])    

print("\nCheck complete. No API request was made.")

# --- CANCELLATION AND AIRPORT CODE CHECK ---

print("\n--- CANCELLATION STATUS CHECK ---")

all_statuses = {}
airport_codes = set()

for section in ("departures", "arrivals"):
    for record in flight_data.get(section, []):
        status = record.get("status") or "Unknown"
        all_statuses[status] = all_statuses.get(status, 0) + 1

        for field in ("departure", "arrival"):
            details = record.get(field) or {}
            code = details.get("airport", {}).get("iata")

            if code:
                airport_codes.add(code)

print("All flight statuses:", all_statuses)
print("Airport codes found:", sorted(airport_codes))
print("Check complete. No API request was made.")

# --- FLIGHT DATE CHECK ---

print("\n--- FLIGHT DATE CHECK ---")

for section in ("departures", "arrivals"):
    dates = set()

    for record in flight_data.get(section, []):
        for field in ("departure", "arrival"):
            details = record.get(field) or {}
            scheduled = details.get("scheduledTime") or {}
            local_time = scheduled.get("local")

            if local_time:
                dates.add(local_time[:10])

    print(f"{section.title()} dates:", sorted(dates))

print("\nCheck complete. No API request was made.")

# --- AIRPORT CODE SUMMARY ---

print("\n--- AIRPORT CODE SUMMARY ---")

for section in ("departures", "arrivals"):
    codes = {}

    for record in flight_data.get(section, []):
        for field in ("departure", "arrival"):
            details = record.get(field) or {}
            airport = details.get("airport") or {}
            code = airport.get("iata")

            if code:
                codes[code] = codes.get(code, 0) + 1

    print(f"{section.title()} airport codes:", codes)

print("\nCheck complete. No API request was made.")