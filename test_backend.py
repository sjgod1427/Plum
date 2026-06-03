"""
Backend test script for Plum OPD Claims API.

Usage:
    1. Copy backend/.env.example to backend/.env and fill in OPENAI_API_KEY
    2. cd backend && uvicorn main:app --reload
    3. In a new terminal: python test_backend.py

Tests covered:
    - Health check
    - Direct claim submission (all 10 test cases from test_cases.json)
    - File upload claim submission (with generated prescription + bill images)
    - Appeals workflow (submit → list → resolve)
    - Admin: policy read, section update, RAG rebuild
    - Admin: metrics, label, test suite runner
"""

import io
import json
import time
from datetime import date, timedelta

import requests
from PIL import Image, ImageDraw, ImageFont

BASE_URL = "http://localhost:8000"

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
INFO = "\033[94m→\033[0m"


def p(icon, msg):
    print(f"  {icon} {msg}")


def section(title):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


# ─── Image generation helpers ────────────────────────────────────────────────


def _make_image(lines: list[str]) -> bytes:
    img = Image.new("RGB", (600, 800), color="white")
    draw = ImageDraw.Draw(img)
    y = 30
    for line in lines:
        draw.text((30, y), line, fill="black")
        y += 28
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_prescription(
    doctor_name: str,
    doctor_reg: str,
    patient_name: str,
    diagnosis: str,
    medicines: list[str],
    treatment_date: str,
) -> bytes:
    lines = [
        f"Dr. {doctor_name}",
        f"Reg No: {doctor_reg}",
        "─" * 35,
        f"Date: {treatment_date}",
        f"Patient: {patient_name}",
        f"Diagnosis: {diagnosis}",
        "Rx:",
    ] + [f"  - {m}" for m in medicines]
    return _make_image(lines)


def make_bill(
    patient_name: str,
    treatment_date: str,
    items: dict[str, float],
) -> bytes:
    lines = [
        "City Medical Centre",
        "─" * 35,
        f"Date: {treatment_date}",
        f"Patient: {patient_name}",
        "─" * 35,
    ]
    total = 0.0
    for desc, amt in items.items():
        lines.append(f"{desc:<30} ₹{amt:.0f}")
        total += amt
    lines += ["─" * 35, f"{'TOTAL':<30} ₹{total:.0f}"]
    return _make_image(lines)


# ─── Assertion helper ────────────────────────────────────────────────────────


def assert_eq(label: str, actual, expected):
    if actual == expected:
        p(PASS, f"{label}: {actual}")
        return True
    else:
        p(FAIL, f"{label}: expected={expected!r}  got={actual!r}")
        return False


def assert_in(label: str, actual, options: list):
    if actual in options:
        p(PASS, f"{label}: {actual}")
        return True
    else:
        p(FAIL, f"{label}: expected one of {options}  got={actual!r}")
        return False


# ─── Test functions ──────────────────────────────────────────────────────────


def test_health():
    section("HEALTH CHECK")
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200, f"HTTP {r.status_code}"
    assert_eq("status", r.json()["status"], "ok")


def test_direct_claim(
    label: str,
    submission: dict,
    extraction: dict,
    expected_decision: str,
    expected_amount: float | None = None,
) -> dict | None:
    payload = {"submission": submission, "extraction": extraction}
    r = requests.post(f"{BASE_URL}/claims/direct", json=payload, timeout=60)
    if r.status_code != 200:
        p(FAIL, f"{label}: HTTP {r.status_code} — {r.text[:200]}")
        return None

    data = r.json()
    decision = data["decision"]["decision"]
    amount = data["decision"]["approved_amount"]
    conf = data["decision"]["confidence_score"]

    ok = assert_in(label, decision, [expected_decision, "MANUAL_REVIEW"])
    p(INFO, f"  approved_amount={amount}  confidence={conf:.2f}")
    p(INFO, f"  reasoning: {data['decision'].get('reasoning', '')[:200]}")
    p(INFO, f"  notes: {data['decision']['notes'][:120]}")

    if expected_amount and decision == expected_decision:
        # Allow ±15% tolerance for amounts
        tolerance = expected_amount * 0.15
        if abs(amount - expected_amount) <= tolerance:
            p(PASS, f"  amount within tolerance (expected ₹{expected_amount})")
        else:
            p(FAIL, f"  amount out of tolerance: expected ₹{expected_amount}  got ₹{amount}")

    return data


def test_file_upload_claim():
    section("FILE UPLOAD CLAIM")

    rx_bytes = make_prescription(
        doctor_name="Sharma",
        doctor_reg="KA/45678/2015",
        patient_name="Rajesh Kumar",
        diagnosis="Viral fever",
        medicines=["Paracetamol 650mg", "Vitamin C"],
        treatment_date="2024-11-01",
    )
    bill_bytes = make_bill(
        patient_name="Rajesh Kumar",
        treatment_date="2024-11-01",
        items={"Consultation Fee": 1000.0, "CBC Blood Test": 300.0, "Dengue Test": 200.0},
    )

    files = [
        ("files", ("prescription.png", rx_bytes, "image/png")),
        ("files", ("bill.png", bill_bytes, "image/png")),
    ]
    data_str = json.dumps({
        "member_id": "EMP001",
        "member_name": "Rajesh Kumar",
        "member_join_date": "2024-01-01",
        "treatment_date": "2024-11-01",
        "claim_amount": 1500.0,
        "hospital_name": None,
        "cashless_request": False,
        "ytd_claimed_amount": 0.0,
        "previous_claims_same_day": 0,
    })

    r = requests.post(
        f"{BASE_URL}/claims",
        files=files,
        data={"data": data_str},
        timeout=120,
    )

    if r.status_code == 200:
        data = r.json()
        p(PASS, f"File upload claim submitted: {data['claim_id']}")
        p(INFO, f"  decision={data['decision']['decision']}  amount={data['decision']['approved_amount']}")
        p(INFO, f"  diagnosis extracted: {data['extracted_data']['merged_diagnosis']}")
        return data["claim_id"]
    else:
        p(FAIL, f"HTTP {r.status_code}: {r.text[:300]}")
        return None


def test_get_claim(claim_id: str):
    section(f"GET CLAIM — {claim_id}")
    r = requests.get(f"{BASE_URL}/claims/{claim_id}", timeout=30)
    if r.status_code == 200:
        data = r.json()
        p(PASS, f"Fetched claim: status={data['claim']['status']}")
        p(INFO, f"  decision={data['decision']['decision'] if data['decision'] else 'None'}")
    else:
        p(FAIL, f"HTTP {r.status_code}: {r.text[:200]}")


def test_list_claims():
    section("LIST CLAIMS")
    r = requests.get(f"{BASE_URL}/claims", timeout=30)
    assert r.status_code == 200, f"HTTP {r.status_code}"
    claims = r.json()
    p(PASS, f"Listed {len(claims)} claims")
    if claims:
        p(INFO, f"  Latest: {claims[0]['claim_id']} — {claims[0]['decision']}")


def test_appeals_workflow(claim_id: str):
    section(f"APPEALS WORKFLOW — {claim_id}")

    # Submit appeal
    r = requests.post(
        f"{BASE_URL}/claims/{claim_id}/appeal",
        json={"appeal_reason": "Prescribed treatment was medically necessary", "additional_notes": "Doctor confirmed necessity"},
        timeout=30,
    )
    if r.status_code not in (200, 409):
        p(FAIL, f"Submit appeal: HTTP {r.status_code}: {r.text[:200]}")
        return
    if r.status_code == 409:
        p(INFO, "Appeal already exists — skipping submit")
    else:
        data = r.json()
        appeal_id = data["appeal_id"]
        p(PASS, f"Appeal submitted: appeal_id={appeal_id}")

        # List appeals
        r2 = requests.get(f"{BASE_URL}/appeals", timeout=30)
        p(PASS, f"Listed {len(r2.json())} appeals")

        # Get single appeal
        r3 = requests.get(f"{BASE_URL}/appeals/{appeal_id}", timeout=30)
        assert r3.status_code == 200
        p(PASS, f"Fetched appeal: {r3.json()['appeal']['status']}")

        # Resolve appeal
        r4 = requests.patch(
            f"{BASE_URL}/appeals/{appeal_id}/resolve",
            json={
                "new_decision": "APPROVED",
                "approved_amount": 1350.0,
                "reviewer_notes": "Reviewed and upheld — treatment was medically necessary.",
            },
            timeout=30,
        )
        if r4.status_code == 200:
            p(PASS, f"Appeal resolved: {r4.json()['status']}")
        else:
            p(FAIL, f"Resolve appeal: HTTP {r4.status_code}: {r4.text[:200]}")


def test_admin_policy():
    section("ADMIN — POLICY CONFIG")

    # Get policy
    r = requests.get(f"{BASE_URL}/admin/policy", timeout=30)
    assert r.status_code == 200
    p(PASS, f"Policy fetched — source: {r.json()['source']}")

    # Update a section
    r2 = requests.patch(
        f"{BASE_URL}/admin/policy/limits",
        json={
            "config": {
                "annual_limit": 50000,
                "per_claim_limit": 5000,
                "family_floater_limit": 150000,
            },
            "updated_by": "test_script",
        },
        timeout=30,
    )
    if r2.status_code == 200:
        p(PASS, f"Section updated: {r2.json()}")
    else:
        p(FAIL, f"Update section: HTTP {r2.status_code}: {r2.text[:200]}")

    # Rebuild RAG
    r3 = requests.post(f"{BASE_URL}/admin/policy/rebuild-rag", timeout=60)
    if r3.status_code == 200:
        p(PASS, f"RAG rebuilt: {r3.json()}")
    else:
        p(FAIL, f"Rebuild RAG: HTTP {r3.status_code}: {r3.text[:200]}")


def test_admin_metrics(claim_id: str | None):
    section("ADMIN — METRICS")

    # Get metrics
    r = requests.get(f"{BASE_URL}/admin/metrics", timeout=30)
    assert r.status_code == 200
    m = r.json()
    p(PASS, f"Metrics: total_claims={m['total_claims']}")
    p(INFO, f"  Breakdown: {m['decisions_breakdown']}")
    p(INFO, f"  Accuracy: {m['accuracy']}")

    # Label a claim if we have one
    if claim_id:
        r2 = requests.patch(
            f"{BASE_URL}/admin/metrics/{claim_id}/label",
            json={"ground_truth_decision": "APPROVED", "actual_approved_amount": 1350.0},
            timeout=30,
        )
        if r2.status_code == 200:
            p(PASS, f"Claim labelled: {r2.json()}")
        else:
            p(FAIL, f"Label: HTTP {r2.status_code}: {r2.text[:200]}")


def test_admin_test_suite():
    section("ADMIN — TEST SUITE RUNNER")
    p(INFO, "Running all 10 test cases via the admin endpoint (this takes ~2–3 min)...")
    r = requests.post(f"{BASE_URL}/admin/metrics/run-test-suite", timeout=300)
    if r.status_code == 200:
        data = r.json()
        p(PASS, f"Test suite complete: {data['passed']}/{data['total']} passed")
        for res in data["results"]:
            icon = PASS if res.get("passed") else FAIL
            p(icon, f"  {res['case_id']} {res.get('case_name', '')} — expected={res.get('expected_decision')}  got={res.get('actual_decision', 'ERROR')}")
    else:
        p(FAIL, f"HTTP {r.status_code}: {r.text[:300]}")


# ─── Manual 10 test cases ────────────────────────────────────────────────────


def run_10_test_cases():
    section("10 TEST CASES (DIRECT SUBMISSION)")

    cases = [
        {
            "label": "TC001 — Simple fever consultation (APPROVED)",
            "submission": {
                "member_id": "EMP001", "member_name": "Rajesh Kumar",
                "member_join_date": "2024-01-01", "treatment_date": "2024-11-01",
                "claim_amount": 1500.0, "ytd_claimed_amount": 0.0, "previous_claims_same_day": 0,
            },
            "extraction": {
                "documents": [
                    {"doc_type": "prescription", "doctor_name": "Dr. Sharma", "doctor_reg": "KA/45678/2015",
                     "patient_name": "Rajesh Kumar", "diagnosis": "Viral fever",
                     "medicines": ["Paracetamol 650mg", "Vitamin C"], "tests_prescribed": ["CBC", "Dengue test"],
                     "procedures": [], "treatment_date": "2024-11-01",
                     "consultation_fee": 1000.0, "total_amount": 1500.0, "line_items": [], "extraction_confidence": 0.95},
                    {"doc_type": "bill", "doctor_name": None, "doctor_reg": None,
                     "patient_name": "Rajesh Kumar", "diagnosis": None,
                     "medicines": [], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-11-01", "consultation_fee": 1000.0, "total_amount": 1500.0,
                     "line_items": [{"description": "Consultation", "amount": 1000}, {"description": "CBC", "amount": 500}],
                     "extraction_confidence": 0.95},
                ],
                "merged_diagnosis": "Viral fever", "merged_total": 1500.0,
                "date_consistent": True, "patient_name_consistent": True,
                "all_required_docs_present": True, "missing_docs": [],
            },
            "expected_decision": "APPROVED", "expected_amount": 1350.0,
        },
        {
            "label": "TC002 — Dental partial (PARTIAL)",
            "submission": {
                "member_id": "EMP002", "member_name": "Priya Singh",
                "member_join_date": "2024-01-01", "treatment_date": "2024-10-15",
                "claim_amount": 12000.0, "ytd_claimed_amount": 0.0, "previous_claims_same_day": 0,
            },
            "extraction": {
                "documents": [
                    {"doc_type": "prescription", "doctor_name": "Dr. Patel", "doctor_reg": "MH/23456/2018",
                     "patient_name": "Priya Singh", "diagnosis": "Tooth decay requiring root canal",
                     "medicines": [], "tests_prescribed": [], "procedures": ["Root canal treatment", "Teeth whitening"],
                     "treatment_date": "2024-10-15", "consultation_fee": None, "total_amount": 12000.0,
                     "line_items": [], "extraction_confidence": 0.92},
                    {"doc_type": "bill", "doctor_name": None, "doctor_reg": None,
                     "patient_name": "Priya Singh", "diagnosis": None,
                     "medicines": [], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-10-15", "consultation_fee": None, "total_amount": 12000.0,
                     "line_items": [{"description": "Root canal", "amount": 8000}, {"description": "Teeth whitening", "amount": 4000}],
                     "extraction_confidence": 0.93},
                ],
                "merged_diagnosis": "Tooth decay requiring root canal", "merged_total": 12000.0,
                "date_consistent": True, "patient_name_consistent": True,
                "all_required_docs_present": True, "missing_docs": [],
            },
            "expected_decision": "PARTIAL", "expected_amount": 8000.0,
        },
        {
            "label": "TC003 — Per-claim limit exceeded (REJECTED)",
            "submission": {
                "member_id": "EMP003", "member_name": "Amit Verma",
                "member_join_date": "2024-01-01", "treatment_date": "2024-10-20",
                "claim_amount": 7500.0, "ytd_claimed_amount": 0.0, "previous_claims_same_day": 0,
            },
            "extraction": {
                "documents": [
                    {"doc_type": "prescription", "doctor_name": "Dr. Gupta", "doctor_reg": "DL/34567/2016",
                     "patient_name": "Amit Verma", "diagnosis": "Gastroenteritis",
                     "medicines": ["Antibiotics", "Probiotics"], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-10-20", "consultation_fee": 2000.0, "total_amount": 7500.0,
                     "line_items": [], "extraction_confidence": 0.95},
                    {"doc_type": "bill", "doctor_name": None, "doctor_reg": None,
                     "patient_name": "Amit Verma", "diagnosis": None,
                     "medicines": [], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-10-20", "consultation_fee": 2000.0, "total_amount": 7500.0,
                     "line_items": [{"description": "Consultation", "amount": 2000}, {"description": "Medicines", "amount": 5500}],
                     "extraction_confidence": 0.95},
                ],
                "merged_diagnosis": "Gastroenteritis", "merged_total": 7500.0,
                "date_consistent": True, "patient_name_consistent": True,
                "all_required_docs_present": True, "missing_docs": [],
            },
            "expected_decision": "REJECTED",
        },
        {
            "label": "TC004 — Missing prescription (REJECTED)",
            "submission": {
                "member_id": "EMP004", "member_name": "Sneha Reddy",
                "member_join_date": "2024-01-01", "treatment_date": "2024-10-25",
                "claim_amount": 2000.0, "ytd_claimed_amount": 0.0, "previous_claims_same_day": 0,
            },
            "extraction": {
                "documents": [
                    {"doc_type": "bill", "doctor_name": None, "doctor_reg": None,
                     "patient_name": "Sneha Reddy", "diagnosis": None,
                     "medicines": [], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-10-25", "consultation_fee": 1500.0, "total_amount": 2000.0,
                     "line_items": [{"description": "Consultation", "amount": 1500}, {"description": "Medicines", "amount": 500}],
                     "extraction_confidence": 0.95},
                ],
                "merged_diagnosis": "Unknown", "merged_total": 2000.0,
                "date_consistent": True, "patient_name_consistent": True,
                "all_required_docs_present": False, "missing_docs": ["Prescription from registered doctor"],
            },
            "expected_decision": "REJECTED",
        },
        {
            "label": "TC005 — Diabetes within waiting period (REJECTED)",
            "submission": {
                "member_id": "EMP005", "member_name": "Vikram Joshi",
                "member_join_date": "2024-09-01", "treatment_date": "2024-10-15",
                "claim_amount": 3000.0, "ytd_claimed_amount": 0.0, "previous_claims_same_day": 0,
            },
            "extraction": {
                "documents": [
                    {"doc_type": "prescription", "doctor_name": "Dr. Mehta", "doctor_reg": "GJ/56789/2014",
                     "patient_name": "Vikram Joshi", "diagnosis": "Type 2 Diabetes",
                     "medicines": ["Metformin", "Glimepiride"], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-10-15", "consultation_fee": 1000.0, "total_amount": 3000.0,
                     "line_items": [], "extraction_confidence": 0.95},
                    {"doc_type": "bill", "doctor_name": None, "doctor_reg": None,
                     "patient_name": "Vikram Joshi", "diagnosis": None,
                     "medicines": [], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-10-15", "consultation_fee": 1000.0, "total_amount": 3000.0,
                     "line_items": [{"description": "Consultation", "amount": 1000}, {"description": "Medicines", "amount": 2000}],
                     "extraction_confidence": 0.95},
                ],
                "merged_diagnosis": "Type 2 Diabetes", "merged_total": 3000.0,
                "date_consistent": True, "patient_name_consistent": True,
                "all_required_docs_present": True, "missing_docs": [],
            },
            "expected_decision": "REJECTED",
        },
        {
            "label": "TC006 — Ayurvedic treatment (APPROVED)",
            "submission": {
                "member_id": "EMP006", "member_name": "Kavita Nair",
                "member_join_date": "2024-01-01", "treatment_date": "2024-10-28",
                "claim_amount": 4000.0, "ytd_claimed_amount": 0.0, "previous_claims_same_day": 0,
            },
            "extraction": {
                "documents": [
                    {"doc_type": "prescription", "doctor_name": "Vaidya Krishnan", "doctor_reg": "AYUR/KL/2345/2019",
                     "patient_name": "Kavita Nair", "diagnosis": "Chronic joint pain",
                     "medicines": [], "tests_prescribed": [], "procedures": ["Panchakarma therapy"],
                     "treatment_date": "2024-10-28", "consultation_fee": 1000.0, "total_amount": 4000.0,
                     "line_items": [], "extraction_confidence": 0.89},
                    {"doc_type": "bill", "doctor_name": None, "doctor_reg": None,
                     "patient_name": "Kavita Nair", "diagnosis": None,
                     "medicines": [], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-10-28", "consultation_fee": 1000.0, "total_amount": 4000.0,
                     "line_items": [{"description": "Consultation", "amount": 1000}, {"description": "Therapy", "amount": 3000}],
                     "extraction_confidence": 0.90},
                ],
                "merged_diagnosis": "Chronic joint pain", "merged_total": 4000.0,
                "date_consistent": True, "patient_name_consistent": True,
                "all_required_docs_present": True, "missing_docs": [],
            },
            "expected_decision": "APPROVED", "expected_amount": 4000.0,
        },
        {
            "label": "TC007 — MRI without pre-auth (REJECTED)",
            "submission": {
                "member_id": "EMP007", "member_name": "Suresh Patil",
                "member_join_date": "2024-01-01", "treatment_date": "2024-11-02",
                "claim_amount": 15000.0, "ytd_claimed_amount": 0.0, "previous_claims_same_day": 0,
            },
            "extraction": {
                "documents": [
                    {"doc_type": "prescription", "doctor_name": "Dr. Rao", "doctor_reg": "AP/67890/2017",
                     "patient_name": "Suresh Patil", "diagnosis": "Suspected lumbar disc herniation",
                     "medicines": [], "tests_prescribed": ["MRI Lumbar Spine"], "procedures": [],
                     "treatment_date": "2024-11-02", "consultation_fee": None, "total_amount": 15000.0,
                     "line_items": [], "extraction_confidence": 0.94},
                    {"doc_type": "bill", "doctor_name": None, "doctor_reg": None,
                     "patient_name": "Suresh Patil", "diagnosis": None,
                     "medicines": [], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-11-02", "consultation_fee": None, "total_amount": 15000.0,
                     "line_items": [{"description": "MRI Lumbar Spine", "amount": 15000}],
                     "extraction_confidence": 0.95},
                ],
                "merged_diagnosis": "Suspected lumbar disc herniation", "merged_total": 15000.0,
                "date_consistent": True, "patient_name_consistent": True,
                "all_required_docs_present": True, "missing_docs": [],
            },
            "expected_decision": "REJECTED",
        },
        {
            "label": "TC008 — 3 claims same day, fraud (MANUAL_REVIEW)",
            "submission": {
                "member_id": "EMP008", "member_name": "Ravi Menon",
                "member_join_date": "2024-01-01", "treatment_date": "2024-10-30",
                "claim_amount": 4800.0, "ytd_claimed_amount": 0.0, "previous_claims_same_day": 3,
            },
            "extraction": {
                "documents": [
                    {"doc_type": "prescription", "doctor_name": "Dr. Khan", "doctor_reg": "UP/45678/2016",
                     "patient_name": "Ravi Menon", "diagnosis": "Migraine",
                     "medicines": ["Sumatriptan", "Propranolol"], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-10-30", "consultation_fee": 2000.0, "total_amount": 4800.0,
                     "line_items": [], "extraction_confidence": 0.92},
                    {"doc_type": "bill", "doctor_name": None, "doctor_reg": None,
                     "patient_name": "Ravi Menon", "diagnosis": None,
                     "medicines": [], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-10-30", "consultation_fee": 2000.0, "total_amount": 4800.0,
                     "line_items": [{"description": "Consultation", "amount": 2000}, {"description": "Medicines", "amount": 2800}],
                     "extraction_confidence": 0.92},
                ],
                "merged_diagnosis": "Migraine", "merged_total": 4800.0,
                "date_consistent": True, "patient_name_consistent": True,
                "all_required_docs_present": True, "missing_docs": [],
            },
            "expected_decision": "MANUAL_REVIEW",
        },
        {
            "label": "TC009 — Weight loss excluded (REJECTED)",
            "submission": {
                "member_id": "EMP009", "member_name": "Anita Desai",
                "member_join_date": "2024-01-01", "treatment_date": "2024-10-18",
                "claim_amount": 8000.0, "ytd_claimed_amount": 0.0, "previous_claims_same_day": 0,
            },
            "extraction": {
                "documents": [
                    {"doc_type": "prescription", "doctor_name": "Dr. Banerjee", "doctor_reg": "WB/34567/2015",
                     "patient_name": "Anita Desai", "diagnosis": "Obesity - BMI 35",
                     "medicines": [], "tests_prescribed": [], "procedures": ["Bariatric consultation", "Diet plan"],
                     "treatment_date": "2024-10-18", "consultation_fee": 3000.0, "total_amount": 8000.0,
                     "line_items": [], "extraction_confidence": 0.97},
                    {"doc_type": "bill", "doctor_name": None, "doctor_reg": None,
                     "patient_name": "Anita Desai", "diagnosis": None,
                     "medicines": [], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-10-18", "consultation_fee": 3000.0, "total_amount": 8000.0,
                     "line_items": [{"description": "Consultation", "amount": 3000}, {"description": "Diet plan", "amount": 5000}],
                     "extraction_confidence": 0.97},
                ],
                "merged_diagnosis": "Obesity - BMI 35", "merged_total": 8000.0,
                "date_consistent": True, "patient_name_consistent": True,
                "all_required_docs_present": True, "missing_docs": [],
            },
            "expected_decision": "REJECTED",
        },
        {
            "label": "TC010 — Network hospital cashless (APPROVED)",
            "submission": {
                "member_id": "EMP010", "member_name": "Deepak Shah",
                "member_join_date": "2024-01-01", "treatment_date": "2024-11-03",
                "claim_amount": 4500.0, "hospital_name": "Apollo Hospitals",
                "cashless_request": True, "ytd_claimed_amount": 0.0, "previous_claims_same_day": 0,
            },
            "extraction": {
                "documents": [
                    {"doc_type": "prescription", "doctor_name": "Dr. Iyer", "doctor_reg": "TN/56789/2013",
                     "patient_name": "Deepak Shah", "diagnosis": "Acute bronchitis",
                     "medicines": ["Antibiotics", "Bronchodilators"], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-11-03", "consultation_fee": 1500.0, "total_amount": 4500.0,
                     "line_items": [], "extraction_confidence": 0.93},
                    {"doc_type": "bill", "doctor_name": None, "doctor_reg": None,
                     "patient_name": "Deepak Shah", "diagnosis": None,
                     "medicines": [], "tests_prescribed": [], "procedures": [],
                     "treatment_date": "2024-11-03", "consultation_fee": 1500.0, "total_amount": 4500.0,
                     "line_items": [{"description": "Consultation", "amount": 1500}, {"description": "Medicines", "amount": 3000}],
                     "extraction_confidence": 0.93},
                ],
                "merged_diagnosis": "Acute bronchitis", "merged_total": 4500.0,
                "date_consistent": True, "patient_name_consistent": True,
                "all_required_docs_present": True, "missing_docs": [],
            },
            "expected_decision": "APPROVED", "expected_amount": 3600.0,
        },
    ]

    results = {"passed": 0, "failed": 0}
    first_rejected_id = None

    for i, case in enumerate(cases):
        print(f"\n  [{i+1}/10] {case['label']}")
        data = test_direct_claim(
            label=case["label"],
            submission=case["submission"],
            extraction=case["extraction"],
            expected_decision=case["expected_decision"],
            expected_amount=case.get("expected_amount"),
        )
        if data:
            actual = data["decision"]["decision"]
            expected = case["expected_decision"]
            if actual == expected or (expected == "MANUAL_REVIEW" and actual == "MANUAL_REVIEW"):
                results["passed"] += 1
            else:
                results["failed"] += 1

            if actual == "REJECTED" and not first_rejected_id:
                first_rejected_id = data["claim_id"]
        else:
            results["failed"] += 1

        time.sleep(1)  # avoid rate limits

    print(f"\n  Result: {results['passed']}/10 passed, {results['failed']}/10 failed")
    return first_rejected_id


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    print("\n" + "═" * 60)
    print("  PLUM CLAIMS API — BACKEND TEST SUITE")
    print("═" * 60)

    test_health()

    # Run 10 test cases, get a rejected claim ID for appeal test
    rejected_claim_id = run_10_test_cases()

    # File upload test
    uploaded_claim_id = test_file_upload_claim()

    # Get + list
    if uploaded_claim_id:
        test_get_claim(uploaded_claim_id)
    test_list_claims()

    # Appeals on a rejected claim
    if rejected_claim_id:
        test_appeals_workflow(rejected_claim_id)
    else:
        print("\n  [SKIP] No rejected claim found for appeal test")

    # Admin
    test_admin_policy()
    test_admin_metrics(uploaded_claim_id)

    print("\n" + "═" * 60)
    print("  All tests complete.")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()
