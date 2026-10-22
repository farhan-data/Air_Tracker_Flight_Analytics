
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Project folder
PROJECT_DIR = Path(__file__).resolve().parent.parent

# CSV report read karein
CSV_FILE = PROJECT_DIR / "airport_delay_summary.csv"
df = pd.read_csv(CSV_FILE)

# Latest available date ka data lein
df["delay_date"] = pd.to_datetime(df["delay_date"])
latest_date = df["delay_date"].max()

latest_df = df[df["delay_date"] == latest_date].copy()
latest_df = latest_df.sort_values(
    "canceled_flights", ascending=False
)

# Cancellation chart
plt.figure(figsize=(10, 6))
plt.bar(
    latest_df["airport_iata"],
    latest_df["canceled_flights"]
)

plt.title(f"Cancelled Flights by Airport - {latest_date.date()}")
plt.xlabel("Airport")
plt.ylabel("Cancelled Flights")
plt.tight_layout()

# Chart save karein
output_file = PROJECT_DIR / "airport_cancellation_chart.png"
plt.savefig(output_file, dpi=150)
plt.show()

print(f"Chart saved to: {output_file}")
