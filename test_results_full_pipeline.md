# Full Pipeline Test Results — EasyOCR + GPT-4o

**Date:** 2026-06-04
**Script:** `test_full_pipeline.py`
**Pipeline:** EasyOCR (local, free) → GPT-4o text structuring → GPT-4o adjudication
**Total elapsed:** 220.4s

---

## Results

| Case | Name | Expected | Got | Amount | Conf | Time | Status |
|------|------|----------|-----|--------|------|------|--------|
| TC001 | Simple Consultation - Approved | APPROVED | APPROVED | ₹1325 | 100% | 23.8s | PASS |
| TC002 | Dental Treatment - Partial Approval | PARTIAL | PARTIAL | ₹8400 | 100% | 22.5s | PASS |
| TC003 | Limit Exceeded - Rejected | REJECTED | REJECTED | ₹0 | 95% | 28.0s | PASS |
| TC004 | Missing Documents - Rejected | REJECTED | REJECTED | ₹0 | 90% | 14.2s | PASS |
| TC005 | Pre-existing Condition - Waiting Period | REJECTED | REJECTED | ₹0 | 100% | 24.7s | PASS |
| TC006 | Alternative Medicine - Approved | APPROVED | APPROVED | ₹4000 | 95% | 24.6s | PASS |
| TC007 | Diagnostic Tests - Pre-auth Required | REJECTED | REJECTED | ₹0 | 80% | 20.3s | PASS |
| TC008 | Fraud Detection - Manual Review | MANUAL_REVIEW | MANUAL_REVIEW | ₹0 | 80% | 19.1s | PASS |
| TC009 | Excluded Treatment - Rejected | REJECTED | REJECTED | ₹0 | 100% | 21.1s | PASS |
| TC010 | Network Hospital - Cashless Approved | APPROVED | APPROVED | ₹3600 | 95% | 22.1s | PASS |

**Result: 10/10 passed**
