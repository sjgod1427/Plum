"""
Seed the production Modal Volume SQLite DB with the 10 known test-case results
from test_results_full_pipeline.md (10/10 passing run).

Usage:
    modal run backend/seed_db.py::seed_db      # insert / overwrite seed data
    modal run backend/seed_db.py::clear_seed   # remove the 10 seed rows (rollback)
"""

import json
import modal

VOLUME_MOUNT = "/data"
volume = modal.Volume.from_name("plum-data", create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("sqlmodel==0.0.21", "python-dotenv==1.0.1", "pydantic-settings==2.5.2")
    .add_local_dir(".", "/app")
)
app = modal.App("plum-seed", image=image)

SEED_DATA = [
    {
        "case_id": "TC001", "case_name": "Simple Consultation - Approved",
        "member_id": "EMP001", "member_name": "Rajesh Kumar",
        "member_join_date": "2024-01-01", "treatment_date": "2024-11-01",
        "claim_amount": 1500.0, "hospital_name": None, "cashless_request": False,
        "decision": "APPROVED", "approved_amount": 1325.0, "confidence_score": 1.00,
        "rejection_reasons": [], "fraud_flags": [],
        "deductions": [{"reason": "10% co-pay on consultation fee", "amount": 175.0}],
        "policy_sections_referenced": ["coverage_consultation", "limits"],
        "notes": "Claim approved. 10% co-pay applied on consultation fee.",
        "next_steps": "Reimbursement will be credited within 5-7 working days.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active, no waiting period. Step 2 (DOCUMENTS): prescription valid. Step 3 (COVERAGE): viral fever covered. Step 4 (LIMITS): ₹1500 within per-claim limit. Step 5 (MEDICAL NECESSITY): diagnosis justifies treatment. APPROVED with 10% co-pay.",
        "ground_truth": "APPROVED", "is_correct": True,
    },
    {
        "case_id": "TC002", "case_name": "Dental Treatment - Partial Approval",
        "member_id": "EMP002", "member_name": "Priya Singh",
        "member_join_date": "2024-01-01", "treatment_date": "2024-10-15",
        "claim_amount": 12000.0, "hospital_name": None, "cashless_request": False,
        "decision": "PARTIAL", "approved_amount": 8400.0, "confidence_score": 1.00,
        "rejection_reasons": ["COSMETIC_PROCEDURE"],
        "fraud_flags": [],
        "deductions": [{"reason": "Teeth whitening excluded as cosmetic procedure", "amount": 3600.0}],
        "policy_sections_referenced": ["coverage_dental", "exclusions"],
        "notes": "Root canal approved under dental sub-limit. Teeth whitening rejected as cosmetic.",
        "next_steps": "Reimbursement of ₹8400 will be processed within 5-7 working days.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active. Step 2 (DOCUMENTS): valid. Step 3 (COVERAGE): root canal covered under dental; teeth whitening is cosmetic — excluded. Step 4 (LIMITS): ₹8000 within dental sub-limit. PARTIAL approval.",
        "ground_truth": "PARTIAL", "is_correct": True,
    },
    {
        "case_id": "TC003", "case_name": "Limit Exceeded - Rejected",
        "member_id": "EMP003", "member_name": "Amit Verma",
        "member_join_date": "2024-01-01", "treatment_date": "2024-10-20",
        "claim_amount": 7500.0, "hospital_name": None, "cashless_request": False,
        "decision": "REJECTED", "approved_amount": 0.0, "confidence_score": 0.95,
        "rejection_reasons": ["PER_CLAIM_EXCEEDED"], "fraud_flags": [],
        "deductions": [],
        "policy_sections_referenced": ["limits"],
        "notes": "Claim amount ₹7500 exceeds per-claim OPD limit of ₹5000.",
        "next_steps": "You may split the claim or appeal with additional documentation.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active. Step 2 (DOCUMENTS): valid. Step 3 (COVERAGE): gastroenteritis covered. Step 4 (LIMITS): ₹7500 exceeds per-claim limit of ₹5000. REJECTED.",
        "ground_truth": "REJECTED", "is_correct": True,
    },
    {
        "case_id": "TC004", "case_name": "Missing Documents - Rejected",
        "member_id": "EMP004", "member_name": "Sneha Reddy",
        "member_join_date": "2024-01-01", "treatment_date": "2024-10-25",
        "claim_amount": 2000.0, "hospital_name": None, "cashless_request": False,
        "decision": "REJECTED", "approved_amount": 0.0, "confidence_score": 0.90,
        "rejection_reasons": ["MISSING_DOCUMENTS"], "fraud_flags": [],
        "deductions": [],
        "policy_sections_referenced": ["claim_requirements"],
        "notes": "Prescription from a registered doctor is mandatory for OPD claims.",
        "next_steps": "Resubmit with a valid prescription from a registered doctor.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active. Step 2 (DOCUMENTS): no prescription found — mandatory document missing. REJECTED.",
        "ground_truth": "REJECTED", "is_correct": True,
    },
    {
        "case_id": "TC005", "case_name": "Pre-existing Condition - Waiting Period",
        "member_id": "EMP005", "member_name": "Vikram Joshi",
        "member_join_date": "2024-09-01", "treatment_date": "2024-10-15",
        "claim_amount": 3000.0, "hospital_name": None, "cashless_request": False,
        "decision": "REJECTED", "approved_amount": 0.0, "confidence_score": 1.00,
        "rejection_reasons": ["WAITING_PERIOD"], "fraud_flags": [],
        "deductions": [],
        "policy_sections_referenced": ["waiting_periods"],
        "notes": "Type 2 Diabetes has a 90-day waiting period. Policy started 2024-09-01; eligible from 2024-11-30.",
        "next_steps": "Resubmit after 2024-11-30.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active but treatment date 2024-10-15 is within 90-day waiting period for diabetes (join date 2024-09-01, eligible 2024-11-30). REJECTED.",
        "ground_truth": "REJECTED", "is_correct": True,
    },
    {
        "case_id": "TC006", "case_name": "Alternative Medicine - Approved",
        "member_id": "EMP006", "member_name": "Kavita Nair",
        "member_join_date": "2024-01-01", "treatment_date": "2024-10-28",
        "claim_amount": 4000.0, "hospital_name": None, "cashless_request": False,
        "decision": "APPROVED", "approved_amount": 4000.0, "confidence_score": 0.95,
        "rejection_reasons": [], "fraud_flags": [],
        "deductions": [],
        "policy_sections_referenced": ["coverage_alternative", "limits"],
        "notes": "Panchakarma therapy covered under alternative medicine. ₹4000 within ₹8000 sub-limit.",
        "next_steps": "Reimbursement will be credited within 5-7 working days.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active. Step 2 (DOCUMENTS): Ayurvedic prescription valid. Step 3 (COVERAGE): alternative medicine covered. Step 4 (LIMITS): ₹4000 within ₹8000 alternative sub-limit. Step 5 (MEDICAL NECESSITY): chronic joint pain justifies therapy. APPROVED.",
        "ground_truth": "APPROVED", "is_correct": True,
    },
    {
        "case_id": "TC007", "case_name": "Diagnostic Tests - Pre-auth Required",
        "member_id": "EMP007", "member_name": "Suresh Patil",
        "member_join_date": "2024-01-01", "treatment_date": "2024-11-02",
        "claim_amount": 15000.0, "hospital_name": None, "cashless_request": False,
        "decision": "REJECTED", "approved_amount": 0.0, "confidence_score": 0.80,
        "rejection_reasons": ["PRE_AUTH_MISSING"], "fraud_flags": [],
        "deductions": [],
        "policy_sections_referenced": ["coverage_diagnostic"],
        "notes": "MRI requires pre-authorization for claims above ₹10000. No pre-auth found.",
        "next_steps": "Obtain pre-authorization and resubmit.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active. Step 2 (DOCUMENTS): valid. Step 3 (COVERAGE): MRI covered but requires pre-auth for amounts above ₹10000; ₹15000 claim has no pre-auth. REJECTED.",
        "ground_truth": "REJECTED", "is_correct": True,
    },
    {
        "case_id": "TC008", "case_name": "Fraud Detection - Manual Review",
        "member_id": "EMP008", "member_name": "Ravi Menon",
        "member_join_date": "2024-01-01", "treatment_date": "2024-10-30",
        "claim_amount": 4800.0, "hospital_name": None, "cashless_request": False,
        "decision": "MANUAL_REVIEW", "approved_amount": 0.0, "confidence_score": 0.80,
        "rejection_reasons": [],
        "fraud_flags": ["3 claims submitted on the same day — potential fraud pattern"],
        "deductions": [],
        "policy_sections_referenced": [],
        "notes": "Flagged for manual review due to 3 claims on the same day.",
        "next_steps": "A claims officer will review within 2-3 business days.",
        "reasoning": "Step 0 (FRAUD): previous_claims_same_day=3 >= 3 threshold. Immediately routed to MANUAL_REVIEW.",
        "ground_truth": "MANUAL_REVIEW", "is_correct": True,
    },
    {
        "case_id": "TC009", "case_name": "Excluded Treatment - Rejected",
        "member_id": "EMP009", "member_name": "Anita Desai",
        "member_join_date": "2024-01-01", "treatment_date": "2024-10-18",
        "claim_amount": 8000.0, "hospital_name": None, "cashless_request": False,
        "decision": "REJECTED", "approved_amount": 0.0, "confidence_score": 1.00,
        "rejection_reasons": ["SERVICE_NOT_COVERED"], "fraud_flags": [],
        "deductions": [],
        "policy_sections_referenced": ["exclusions"],
        "notes": "Weight loss treatments and obesity management are explicitly excluded.",
        "next_steps": "This treatment category is not covered under your policy.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active. Step 2 (DOCUMENTS): valid. Step 3 (COVERAGE): bariatric consultation and weight loss diet plan are explicitly excluded. REJECTED.",
        "ground_truth": "REJECTED", "is_correct": True,
    },
    {
        "case_id": "TC010", "case_name": "Network Hospital - Cashless Approved",
        "member_id": "EMP010", "member_name": "Deepak Shah",
        "member_join_date": "2024-01-01", "treatment_date": "2024-11-03",
        "claim_amount": 4500.0, "hospital_name": "Apollo Hospitals", "cashless_request": True,
        "decision": "APPROVED", "approved_amount": 3600.0, "confidence_score": 0.95,
        "rejection_reasons": [], "fraud_flags": [],
        "deductions": [{"reason": "20% network hospital discount", "amount": 900.0}],
        "policy_sections_referenced": ["network_hospitals", "coverage_consultation"],
        "notes": "Apollo Hospitals is a network hospital. 20% cashless discount applied.",
        "next_steps": "Cashless claim approved. Settlement directly with hospital.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active. Step 2 (DOCUMENTS): valid. Step 3 (COVERAGE): acute bronchitis covered. Step 4 (LIMITS): within limits. Step 5 (MEDICAL NECESSITY): justified. Network hospital: 20% discount applied. APPROVED.",
        "ground_truth": "APPROVED", "is_correct": True,
    },
]


@app.function(volumes={VOLUME_MOUNT: volume})
def seed_db():
    import os, sys
    sys.path.insert(0, "/app")
    os.environ.setdefault("DATABASE_URL", f"sqlite:////{VOLUME_MOUNT}/claims.db")
    os.environ.setdefault("OPENAI_API_KEY", "placeholder")

    from datetime import datetime
    from sqlmodel import Session, select
    from database import engine, create_db_and_tables
    from models import Claim, ClaimDecision, ClaimDocument, EvaluationLog

    create_db_and_tables()
    now = datetime.utcnow().isoformat()

    with Session(engine) as session:
        for row in SEED_DATA:
            claim_id = f"CLM_{row['case_id']}"

            # Delete existing records for this ID (idempotent upsert)
            for r in session.exec(select(ClaimDecision).where(ClaimDecision.claim_id == claim_id)).all():
                session.delete(r)
            for r in session.exec(select(EvaluationLog).where(EvaluationLog.claim_id == claim_id)).all():
                session.delete(r)
            for r in session.exec(select(ClaimDocument).where(ClaimDocument.claim_id == claim_id)).all():
                session.delete(r)
            existing = session.get(Claim, claim_id)
            if existing:
                session.delete(existing)
            session.commit()

            # Insert Claim
            session.add(Claim(
                id=claim_id,
                member_id=row["member_id"],
                member_name=row["member_name"],
                member_join_date=row["member_join_date"],
                treatment_date=row["treatment_date"],
                claim_amount=row["claim_amount"],
                hospital_name=row["hospital_name"],
                cashless_request=row["cashless_request"],
                ytd_claimed_amount=0.0,
                previous_claims_same_day=3 if row["case_id"] == "TC008" else 0,
                status="PROCESSED",
                test_case_id=row["case_id"],
                created_at=now,
            ))

            # Insert ClaimDecision
            session.add(ClaimDecision(
                claim_id=claim_id,
                reasoning=row["reasoning"],
                decision=row["decision"],
                approved_amount=row["approved_amount"],
                rejection_reasons=json.dumps(row["rejection_reasons"]),
                deductions=json.dumps(row["deductions"]),
                confidence_score=row["confidence_score"],
                fraud_flags=json.dumps(row["fraud_flags"]),
                policy_sections_referenced=json.dumps(row["policy_sections_referenced"]),
                notes=row["notes"],
                next_steps=row["next_steps"],
                created_at=now,
            ))

            # Insert EvaluationLog
            session.add(EvaluationLog(
                claim_id=claim_id,
                ai_decision=row["decision"],
                ground_truth_decision=row["ground_truth"],
                is_correct=row["is_correct"],
                error_type=None,
                amount_deviation=None,
                created_at=now,
            ))

            session.commit()
            print(f"  ✓ {claim_id} — {row['decision']}")

    print(f"\nSeeded {len(SEED_DATA)} test cases into {VOLUME_MOUNT}/claims.db")


@app.function(volumes={VOLUME_MOUNT: volume})
def clear_seed():
    """Rollback: removes only the 10 seeded test-case rows."""
    import os, sys
    sys.path.insert(0, "/app")
    os.environ.setdefault("DATABASE_URL", f"sqlite:////{VOLUME_MOUNT}/claims.db")
    os.environ.setdefault("OPENAI_API_KEY", "placeholder")

    from sqlmodel import Session, select
    from database import engine
    from models import Claim, ClaimDecision, ClaimDocument, EvaluationLog

    with Session(engine) as session:
        for row in SEED_DATA:
            claim_id = f"CLM_{row['case_id']}"
            for r in session.exec(select(ClaimDecision).where(ClaimDecision.claim_id == claim_id)).all():
                session.delete(r)
            for r in session.exec(select(EvaluationLog).where(EvaluationLog.claim_id == claim_id)).all():
                session.delete(r)
            for r in session.exec(select(ClaimDocument).where(ClaimDocument.claim_id == claim_id)).all():
                session.delete(r)
            existing = session.get(Claim, claim_id)
            if existing:
                session.delete(existing)
            session.commit()
            print(f"  ✗ cleared {claim_id}")

    print("Rollback complete — seed data removed.")
