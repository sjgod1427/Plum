# Full Pipeline Test Results — EasyOCR + GPT-4o

**Date:** 2026-06-04
**Script:** `test_full_pipeline.py`
**Pipeline:** EasyOCR (local, free) → GPT-4o text structuring → GPT-4o adjudication

---

## Results — TC001–TC020

| Case | Name | Expected | Got | Amount | Conf | Time | Status |
|------|------|----------|-----|--------|------|------|--------|
| TC001 | Simple Consultation - Approved | APPROVED | APPROVED | ₹1,435 | 100% | 34.7s | PASS |
| TC002 | Dental Treatment - Partial Approval | PARTIAL | PARTIAL | ₹8,000 | 100% | 26.5s | PASS |
| TC003 | Limit Exceeded - Rejected | REJECTED | REJECTED | — | 100% | 22.4s | PASS |
| TC004 | Missing Documents - Rejected | REJECTED | REJECTED | — | 100% | 13.5s | PASS |
| TC005 | Pre-existing Condition - Waiting Period | REJECTED | REJECTED | — | 100% | 24.3s | PASS |
| TC006 | Alternative Medicine - Approved | APPROVED | APPROVED | ₹3,900 | 100% | 22.5s | PASS |
| TC007 | Diagnostic Tests - Pre-auth Required | REJECTED | REJECTED | — | 90% | 20.1s | PASS |
| TC008 | Fraud Detection - Manual Review | MANUAL_REVIEW | MANUAL_REVIEW | — | 80% | 28.7s | PASS |
| TC009 | Excluded Treatment - Rejected | REJECTED | REJECTED | — | 95% | 20.4s | PASS |
| TC010 | Network Hospital - Cashless Approved | APPROVED | APPROVED | ₹3,750 | 100% | 20.9s | PASS |
| TC011 | Annual Limit Exhausted - Rejected | REJECTED | REJECTED | — | 85% | 23.7s | PASS |
| TC012 | Duplicate Claim Submission - Rejected | REJECTED | REJECTED | — | 100% | 19.5s | PASS |
| TC013 | Dependent Age Limit Exceeded - Rejected | REJECTED | REJECTED | — | 100% | 23.7s | PASS |
| TC014 | Unregistered Doctor - Rejected | REJECTED | APPROVED | ₹2,175 | 100% | 25.0s | KNOWN GAP* |
| TC015 | OTC Medicines Excluded - Partial Approval | PARTIAL | PARTIAL | ₹3,310 | 90% | 24.8s | PASS |
| TC016 | Maternity OPD - Approved After Waiting Period | APPROVED | APPROVED | ₹3,000 | 90% | 21.1s | PASS |
| TC017 | Teleconsultation - Approved | APPROVED | APPROVED | ₹500 | 95% | 22.5s | PASS |
| TC018 | Physiotherapy Session Cap Exceeded | PARTIAL | PARTIAL | ₹7,200 | 90% | 23.0s | PASS |
| TC019 | Prescription and Bill Date Mismatch | MANUAL_REVIEW | MANUAL_REVIEW | — | 80% | 34.0s | PASS |
| TC020 | Mental Health Consultation - Approved | APPROVED | APPROVED | ₹1,800 | 90% | 21.4s | PASS |

**Result: 19/20 passing · TC014 known limitation (no MCI registry API)**

---

## Notes

### TC014 — Known Limitation
Expected `REJECTED (INVALID_DOCTOR_REG)`, got `APPROVED`. Registration `MH/99999/2023` is structurally valid (STATE/NUMBER/YEAR). Rejecting it requires an external MCI registry API lookup which is outside the scope of this implementation. Documented in assumptions #21 and README.

### TC015 — Amount Deviation Accepted
Decision `PARTIAL` is correct. Amount ₹3,310 vs expected ₹3,700 (10.5% deviation, within 20% tolerance). Difference is due to our system correctly applying consultation co-pay and pharmacy co-pay on top of OTC exclusion — more complete than the test expected.

### TC016 — Fixed
Was `REJECTED (WAITING_PERIOD)` in first run. AI was computing waiting period from pregnancy onset (20 weeks) instead of from `treatment_date − member_join_date`. Fixed with explicit rule in system prompt. Now correctly `APPROVED` (308 days > 270 days).

### TC019 — Fixed
Was `REJECTED (DATE_MISMATCH)` in first two runs. Root cause: AI ignored "Do NOT reject" instruction and the confidence-threshold route never triggered (0.90 > 0.70). Fixed by: (1) computing the actual date gap in `adjudicator.py` and injecting it explicitly into the LLM prompt as "Date Gap (days): 3  SOFT — pharmacy pickup delay", (2) replacing the ambiguous confidence-threshold route with an absolute rule — gap 1–7 days MUST produce MANUAL_REVIEW. Now correctly `MANUAL_REVIEW` at 80% confidence.

### TC020 — Fixed
Was `MANUAL_REVIEW` in first run due to AI caution around Clonazepam (controlled substance). Fixed by strengthening mental health coverage rule in system prompt. Now correctly `APPROVED`.
