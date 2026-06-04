"""
Email test suite — runs three checks:
  1. Config check (keys set, FROM email set)
  2. Admin email in DB
  3. Simple SendGrid send
  4. Full agentic MANUAL_REVIEW email (OpenAI Agents SDK + SendGrid)
"""
import os, sys, json
os.environ.setdefault("DATABASE_URL", "sqlite:///./claims.db")
sys.path.insert(0, os.path.dirname(__file__))

from config import settings

print("=== 1. Config Check ===")
print(f"SENDGRID_API_KEY set : {bool(settings.SENDGRID_API_KEY)}")
print(f"SENDGRID_FROM_EMAIL  : {settings.SENDGRID_FROM_EMAIL!r}")
print(f"OPENAI_API_KEY set   : {bool(settings.OPENAI_API_KEY)}")

print("\n=== 2. Admin Email in DB ===")
from sqlmodel import Session, select, create_engine
from models import PolicyConfig
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
with Session(engine) as session:
    config = session.exec(select(PolicyConfig).where(PolicyConfig.section == "admin_config")).first()
    if config:
        data = json.loads(config.config_json)
        admin_email = data.get("reviewer_email")
        print(f"reviewer_email: {admin_email!r}")
    else:
        admin_email = None
        print("No admin_config found — save email via /admin/policy first")

print("\n=== 3. Full Claim Endpoint → MANUAL_REVIEW → Agentic Email ===")
print("Submitting TC008 (Ravi Menon, 3 same-day claims) via POST /claims/direct ...")
import requests

payload = {
    "submission": {
        "member_id": "EMP008",
        "member_name": "Ravi Menon",
        "member_join_date": "2024-01-01",
        "treatment_date": "2024-10-30",
        "claim_amount": 4800.0,
        "hospital_name": None,
        "cashless_request": False,
        "ytd_claimed_amount": 0.0,
        "previous_claims_same_day": 3,
    },
    "extraction": {
        "documents": [
            {
                "doc_type": "prescription",
                "doctor_name": "Dr. Khan",
                "doctor_reg": "UP/45678/2016",
                "patient_name": "Ravi Menon",
                "diagnosis": "Migraine",
                "medicines": ["Sumatriptan", "Propranolol"],
                "tests_prescribed": [],
                "procedures": [],
                "treatment_date": "2024-10-30",
                "consultation_fee": 2000.0,
                "total_amount": 4800.0,
                "line_items": [],
                "extraction_confidence": 0.92,
            },
            {
                "doc_type": "bill",
                "doctor_name": None,
                "doctor_reg": None,
                "patient_name": "Ravi Menon",
                "diagnosis": None,
                "medicines": [],
                "tests_prescribed": [],
                "procedures": [],
                "treatment_date": "2024-10-30",
                "consultation_fee": 2000.0,
                "total_amount": 4800.0,
                "line_items": [
                    {"description": "Consultation", "amount": 2000},
                    {"description": "Medicines", "amount": 2800},
                ],
                "extraction_confidence": 0.92,
            },
        ],
        "merged_diagnosis": "Migraine",
        "merged_total": 4800.0,
        "date_consistent": True,
        "patient_name_consistent": True,
        "all_required_docs_present": True,
        "missing_docs": [],
    },
}

r = requests.post("http://localhost:8000/claims/direct", json=payload, timeout=60)
if r.status_code == 200:
    data = r.json()
    decision = data["decision"]["decision"]
    print(f"Claim ID  : {data['claim_id']}")
    print(f"Decision  : {decision}")
    print(f"Confidence: {data['decision']['confidence_score']:.0%}")
    if decision == "MANUAL_REVIEW":
        print("MANUAL_REVIEW triggered — agentic email should have been sent. Check inbox.")
    else:
        print(f"WARNING: Expected MANUAL_REVIEW, got {decision}")
else:
    print(f"FAILED: HTTP {r.status_code} — {r.text[:300]}")
