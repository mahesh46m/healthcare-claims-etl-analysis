"""Generate synthetic healthcare claims with realistic-looking defects. No real data."""
import numpy as np
import pandas as pd

PROCS = {  # procedure code -> (description, typical allowed amount)
    "99213": ("Office visit, established", 95), "99214": ("Office visit, detailed", 140),
    "80053": ("Metabolic panel", 30), "71046": ("Chest X-ray", 70),
    "93000": ("ECG", 45), "97110": ("Therapeutic exercise", 60),
    "45378": ("Colonoscopy", 900), "70553": ("Brain MRI", 1100),
}
PAYERS = ["Payer A", "Payer B", "Payer C", "Payer D"]
STATUSES = ["PAID", "DENIED", "PENDING"]


def generate(n=20_000, seed=7):
    rng = np.random.default_rng(seed)
    codes = rng.choice(list(PROCS), n, p=[.30, .18, .14, .09, .09, .10, .05, .05])
    base = np.array([PROCS[c][1] for c in codes], dtype=float)
    billed = np.round(base * rng.uniform(1.8, 3.2, n), 2)
    allowed = np.round(base * rng.uniform(0.8, 1.2, n), 2)
    svc = pd.to_datetime("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D")
    df = pd.DataFrame({
        "claim_id": [f"C{i:07d}" for i in range(n)],
        "patient_id": [f"P{p:05d}" for p in rng.integers(1, 4000, n)],
        "provider_id": [f"PR{p:03d}" for p in rng.integers(1, 120, n)],
        "payer": rng.choice(PAYERS, n),
        "procedure_code": codes,
        "service_date": svc,
        "billed_amount": billed,
        "allowed_amount": allowed,
        "status": rng.choice(STATUSES, n, p=[.82, .12, .06]),
    })
    df["paid_amount"] = np.where(df.status == "PAID", np.round(df.allowed_amount * rng.uniform(.75, .95, n), 2),
                                 np.where(df.status == "DENIED", 0.0, np.nan))
    df["paid_date"] = np.where(df.status == "PAID",
                               df.service_date + pd.to_timedelta(rng.integers(10, 60, n), unit="D"), pd.NaT)
    df["paid_date"] = pd.to_datetime(df["paid_date"])

    # ---- inject defects ----
    pick = lambda k: rng.choice(n, k, replace=False)
    dup = df.iloc[pick(150)].copy()                      # exact duplicate rows
    df.loc[pick(120), "procedure_code"] = "XXXXX"        # invalid code
    df.loc[pick(100), "billed_amount"] = np.nan          # missing billed
    df.loc[pick(60), "billed_amount"] = -abs(df.billed_amount.median())  # negative
    df.loc[pick(80), "paid_date"] = pd.NaT               # paid claim without date
    idx = pick(60)                                       # paid date before service date
    df.loc[idx, "paid_date"] = df.loc[idx, "service_date"] - pd.Timedelta(days=5)
    df.loc[pick(40), "paid_amount"] = df.paid_amount.max() + 5000  # paid > allowed (and an outlier)
    df.loc[pick(50), "payer"] = rng.choice(["payer a ", "PAYER B", " Payer c"], 50)  # messy labels
    # a few outlier providers that bill far above peers
    bad = ["PR007", "PR042"]
    m = df.provider_id.isin(bad)
    df.loc[m, "billed_amount"] = df.loc[m, "billed_amount"] * 4
    return pd.concat([df, dup], ignore_index=True).sample(frac=1, random_state=seed).reset_index(drop=True)


if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    out = generate()
    out.to_csv("data/claims_raw.csv", index=False)
    print(f"wrote data/claims_raw.csv ({len(out):,} rows)")
