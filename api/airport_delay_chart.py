import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Project folder ka path
PROJECT_DIR = Path(__file__).resolve().parent.parent

# CSV report padhein
CSV_FILE = PROJECT_DIR / "airport_delay_summary.csv"
df = pd.read_csv(CSV_FILE)

# Sirf latest available date ka data use karein
df["delay_date"] = pd.to_datetime(df["delay_date"])
latest_date = df["delay_date"].max()

latest_df = df[df["delay_date"] == latest_date].copy()
latest_df = latest_df.sort_values("total_flights", ascending=False)

# Bar chart banayein
plt.figure(figsize=(10, 6))
plt.bar(latest_df["airport_iata"], latest_df["total_flights"])

plt.title(f"Total Flights by Airport - {latest_date.date()}")
plt.xlabel("Airport")
plt.ylabel("Total Flights")
plt.tight_layout()

# Chart ko project folder mein save karein
output_file = PROJECT_DIR / "airport_flight_chart.png"
plt.savefig(output_file, dpi=150)
plt.show()

print(f"Chart saved to: {output_file}")
