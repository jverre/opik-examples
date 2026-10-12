"""Generate data/solar_output.csv: 90 days x 6 inverters for a fictional farm.

Deterministic (fixed seed), so the shipped CSV is reproducible. Three
anomalies are planted for the agent to find:

  1. INV-04 produces 0 kWh for six days (Apr 14-19) with ground-fault code GF-17.
  2. INV-02 reports exactly 412.5 kWh for twelve days (Apr 20 - May 1) while
     irradiance swings: a stuck meter, with no fault code to give it away.
  3. INV-06 loses about 12% of its yield from May 10 onward (soiling or
     shading), again with no fault code.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).parent / "data" / "solar_output.csv"
START = date(2026, 3, 1)
DAYS = 90
INVERTERS = ["INV-01", "INV-02", "INV-03", "INV-04", "INV-05", "INV-06"]
KWH_PER_IRRADIANCE = 205.0  # 250 kWp array, ~82% performance ratio

rng = random.Random(2026)
unit_factor = {inv: rng.uniform(0.97, 1.03) for inv in INVERTERS}

rows = []
for d in range(DAYS):
    day = START + timedelta(days=d)
    season = 3.2 + 3.0 * d / DAYS  # spring ramp-up
    irradiance = round(max(0.8, rng.gauss(season, 1.3)), 2)
    for inv in INVERTERS:
        energy = irradiance * KWH_PER_IRRADIANCE * unit_factor[inv] * rng.gauss(1.0, 0.012)
        fault, minutes = "", 0

        if inv == "INV-04" and date(2026, 4, 14) <= day <= date(2026, 4, 19):
            energy, fault, minutes = 0.0, "GF-17", 1440
        elif inv == "INV-02" and date(2026, 4, 20) <= day <= date(2026, 5, 1):
            energy = 412.5
        elif inv == "INV-06" and day >= date(2026, 5, 10):
            energy *= 0.88
        elif rng.random() < 0.012:  # rare, short, harmless trips
            fault, minutes = "DC-03", rng.choice([10, 20, 35])
            energy *= 1 - minutes / 600

        rows.append([day.isoformat(), inv, round(energy, 1), irradiance, fault, minutes])

OUT.parent.mkdir(exist_ok=True)
with OUT.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "inverter_id", "energy_kwh", "irradiance_kwh_m2", "fault_code", "fault_minutes"])
    w.writerows(rows)
print(f"wrote {len(rows)} rows to {OUT}")
