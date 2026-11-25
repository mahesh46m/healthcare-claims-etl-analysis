import unittest
import pandas as pd
from src.clean_validate import clean


def row(**kw):
    base = dict(claim_id="C1", patient_id="P1", provider_id="PR1", payer="Payer A", procedure_code="99213",
                service_date="2025-03-01", billed_amount=200.0, allowed_amount=100.0, status="PAID",
                paid_amount=80.0, paid_date="2025-04-01")
    base.update(kw)
    return base


class CleanTests(unittest.TestCase):
    def test_valid_row_passes_and_payer_normalised(self):
        good, rej, rep = clean(pd.DataFrame([row(payer=" payer a ")]))
        self.assertEqual(len(good), 1)
        self.assertEqual(good.payer.iloc[0], "Payer A")

    def test_rules_reject(self):
        df = pd.DataFrame([row(claim_id="C2", procedure_code="XXXXX"),
                           row(claim_id="C3", billed_amount=-5),
                           row(claim_id="C4", paid_amount=500.0),
                           row(claim_id="C5", paid_date="2025-02-01")])
        good, rej, rep = clean(df)
        self.assertEqual(len(good), 0)
        self.assertEqual(rep["rows_rejected"], 4)

    def test_duplicates_removed(self):
        good, _, rep = clean(pd.DataFrame([row(), row()]))
        self.assertEqual(len(good), 1)
        self.assertEqual(rep["exact_duplicates_removed"], 1)


if __name__ == "__main__":
    unittest.main()
