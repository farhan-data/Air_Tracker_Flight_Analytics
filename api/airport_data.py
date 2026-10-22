import json
import os
from pathlib import Path
import mysql.connector

# Load environment variables from the project-root .env file
env_path = Path(__file__).resolve().parent.parent / ".env"

if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

db = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST", "localhost"),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE", "air_tracker"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
)
with open("airport_data.json", "r", encoding="utf-8") as file:
    all_airports = json.load(file)

print("json airports loaded:", len(all_airports))    

airport_list = []

for data in all_airports:
    airport = {
        "icao_code" : data["icao"],
        "iata_code": data["iata"],
        "short_name": data["shortName"],
        "full_name": data["fullName"],
        "municipality_name": data["municipalityName"],
        "location": data["location"],
        "elevation": data["elevation"],
        "country": data["country"],
        "continent": data["continent"],
        "time_zone": data["timeZone"]
    }

    airport_list.append(airport)

print("Total processed airports:", len(airport_list))
print(airport_list[0])

cursor = db.cursor()

insert_query = """
INSERT INTO airport
(icao_code, iata_code, name, city, country, continent, latitude, longitude, timeZone)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

for airport in airport_list:

    cursor.execute(
        insert_query,
        (
            airport["icao_code"],
            airport["iata_code"],
            airport["full_name"],
            airport["municipality_name"],
            airport["country"]["name"],
            airport["continent"]["name"],
            airport["location"]["lat"],
            airport["location"]["lon"],
            airport["time_zone"]
        )
    )

db.commit()

print("15 airports inserted successfully!")

cursor.close()
db.close()
