"""End to end: generate -> clean/validate -> analyze. Run: python run_pipeline.py"""
import json, os
import pandas as pd
from src.generate_claims import generate
from src.clean_validate import clean
from src.analyze import run

os.makedirs("data", exist_ok=True)
os.makedirs("output", exist_ok=True)

raw = generate()
raw.to_csv("data/claims_raw.csv", index=False)
good, rejected, report = clean(pd.read_csv("data/claims_raw.csv", parse_dates=["service_date", "paid_date"]))
good.to_csv("data/claims_clean.csv", index=False)
rejected.to_csv("output/rejected_claims.csv", index=False)
json.dump(report, open("output/validation_report.json", "w"), indent=2)

by_payer, by_proc, prov = run(good)
print("Validation report:\n" + json.dumps(report, indent=2))
print("\nBy payer:\n", by_payer)
print("\nFlagged providers:\n", prov[prov.flag])
