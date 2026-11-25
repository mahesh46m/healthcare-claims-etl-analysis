"""Clean and validate raw claims. Returns clean rows, rejected rows and a validation report."""
import numpy as np
import pandas as pd

VALID_CODES = {"99213", "99214", "80053", "71046", "93000", "97110", "45378", "70553"}


def clean(raw: pd.DataFrame):
    df = raw.copy()
    report = {"rows_in": len(df)}

    for c in ("service_date", "paid_date"):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["payer"] = df["payer"].astype(str).str.strip().str.title()

    report["exact_duplicates_removed"] = int(df.duplicated().sum())
    df = df.drop_duplicates()
    # same claim_id with differing fields (a re-submission): keep the first occurrence
    report["duplicate_claim_ids_removed"] = int(df.claim_id.duplicated().sum())
    df = df[~df.claim_id.duplicated()]

    rules = {
        "invalid_procedure_code": ~df.procedure_code.isin(VALID_CODES),
        "missing_billed_amount": df.billed_amount.isna(),
        "non_positive_billed_amount": df.billed_amount <= 0,
        "paid_without_paid_date": (df.status == "PAID") & df.paid_date.isna(),
        "paid_before_service": df.paid_date < df.service_date,
        "paid_exceeds_allowed": df.paid_amount > df.allowed_amount * 1.0001,
    }
    reasons = pd.Series("", index=df.index)
    for name, mask in rules.items():
        mask = mask.fillna(False)
        report[name] = int(mask.sum())
        reasons = reasons.mask(mask, reasons + name + ";")
    bad = reasons != ""
    rejected = df[bad].assign(reject_reasons=reasons[bad].str.rstrip(";"))
    good = df[~bad].copy()
    good["days_to_pay"] = (good.paid_date - good.service_date).dt.days
    report["rows_rejected"] = int(bad.sum())
    report["rows_clean"] = len(good)
    return good, rejected, report
