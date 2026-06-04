"""
Modal deployment for Plum OPD Claims API.

First-time setup (run once):
    modal secret create plum-secrets OPENAI_API_KEY=sk-...

Deploy (production):
    cd backend && modal deploy modal_app.py

Serve (hot-reload for testing):
    cd backend && modal serve modal_app.py
"""

import modal

VOLUME_MOUNT = "/data"

# ── Persistent volume — stores SQLite DB, ChromaDB, uploaded files ────────────
volume = modal.Volume.from_name("plum-data", create_if_missing=True)

# ── Container image ───────────────────────────────────────────────────────────
image = (
    modal.Image.debian_slim(python_version="3.12")
    # System libs required by OpenCV (EasyOCR dependency)
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install(
        "fastapi==0.115.0",
        "uvicorn[standard]==0.30.6",
        "sqlmodel==0.0.21",
        "openai>=1.50.0",
        "chromadb==0.5.15",
        "python-multipart==0.0.12",
        "python-dotenv==1.0.1",
        "pydantic-settings==2.5.2",
        "pymupdf==1.24.11",
        "pillow==10.4.0",
        "easyocr",
        "requests==2.32.3",
    )
    # Pre-download EasyOCR models at build time so first request isn't slow
    .run_commands(
        "python -c \"import easyocr; easyocr.Reader(['en'], gpu=False, verbose=False)\""
    )
    # Bake entire backend directory into the image (must come last per Modal rules)
    .add_local_dir(".", "/app")
)

# ── Modal app ─────────────────────────────────────────────────────────────────
app = modal.App("plum-claims-api", image=image)


@app.function(
    secrets=[modal.Secret.from_name("plum-secrets")],
    volumes={VOLUME_MOUNT: volume},
    memory=2048,       # EasyOCR needs ~1.5GB
    timeout=300,       # 5 min — allow for OCR + adjudication on cold start
)
@modal.concurrent(max_inputs=10)
@modal.asgi_app()
def fastapi_app():
    import os
    import sys

    sys.path.insert(0, "/app")

    # Point all paths at the persistent volume
    os.environ.setdefault("DATABASE_URL",       f"sqlite:////{VOLUME_MOUNT}/claims.db")
    os.environ.setdefault("CHROMA_PERSIST_DIR",  f"{VOLUME_MOUNT}/chroma_db")
    os.environ.setdefault("UPLOAD_DIR",          f"{VOLUME_MOUNT}/uploads")
    os.environ.setdefault("POLICY_TERMS_PATH",   "/app/policy_terms.json")
    os.environ.setdefault("ALLOWED_ORIGINS",     "*")

    from main import app as fastapi_application
    return fastapi_application


# ── Seed / rollback helpers ───────────────────────────────────────────────────

import json as _json

_SEED_DATA = [
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
        "rejection_reasons": ["COSMETIC_PROCEDURE"], "fraud_flags": [],
        "deductions": [{"reason": "Teeth whitening excluded as cosmetic procedure", "amount": 3600.0}],
        "policy_sections_referenced": ["coverage_dental", "exclusions"],
        "notes": "Root canal approved under dental sub-limit. Teeth whitening rejected as cosmetic.",
        "next_steps": "Reimbursement of ₹8400 will be processed within 5-7 working days.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active. Step 2 (DOCUMENTS): valid. Step 3 (COVERAGE): root canal covered; teeth whitening cosmetic — excluded. Step 4 (LIMITS): ₹8000 within dental sub-limit. PARTIAL approval.",
        "ground_truth": "PARTIAL", "is_correct": True,
    },
    {
        "case_id": "TC003", "case_name": "Limit Exceeded - Rejected",
        "member_id": "EMP003", "member_name": "Amit Verma",
        "member_join_date": "2024-01-01", "treatment_date": "2024-10-20",
        "claim_amount": 7500.0, "hospital_name": None, "cashless_request": False,
        "decision": "REJECTED", "approved_amount": 0.0, "confidence_score": 0.95,
        "rejection_reasons": ["PER_CLAIM_EXCEEDED"], "fraud_flags": [], "deductions": [],
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
        "rejection_reasons": ["MISSING_DOCUMENTS"], "fraud_flags": [], "deductions": [],
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
        "rejection_reasons": ["WAITING_PERIOD"], "fraud_flags": [], "deductions": [],
        "policy_sections_referenced": ["waiting_periods"],
        "notes": "Type 2 Diabetes has a 90-day waiting period. Policy started 2024-09-01; eligible from 2024-11-30.",
        "next_steps": "Resubmit after 2024-11-30.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): treatment date 2024-10-15 is within 90-day waiting period for diabetes (join 2024-09-01, eligible 2024-11-30). REJECTED.",
        "ground_truth": "REJECTED", "is_correct": True,
    },
    {
        "case_id": "TC006", "case_name": "Alternative Medicine - Approved",
        "member_id": "EMP006", "member_name": "Kavita Nair",
        "member_join_date": "2024-01-01", "treatment_date": "2024-10-28",
        "claim_amount": 4000.0, "hospital_name": None, "cashless_request": False,
        "decision": "APPROVED", "approved_amount": 4000.0, "confidence_score": 0.95,
        "rejection_reasons": [], "fraud_flags": [], "deductions": [],
        "policy_sections_referenced": ["coverage_alternative", "limits"],
        "notes": "Panchakarma therapy covered under alternative medicine. ₹4000 within ₹8000 sub-limit.",
        "next_steps": "Reimbursement will be credited within 5-7 working days.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active. Step 2 (DOCUMENTS): Ayurvedic prescription valid. Step 3 (COVERAGE): alternative medicine covered. Step 4 (LIMITS): ₹4000 within ₹8000 sub-limit. APPROVED.",
        "ground_truth": "APPROVED", "is_correct": True,
    },
    {
        "case_id": "TC007", "case_name": "Diagnostic Tests - Pre-auth Required",
        "member_id": "EMP007", "member_name": "Suresh Patil",
        "member_join_date": "2024-01-01", "treatment_date": "2024-11-02",
        "claim_amount": 15000.0, "hospital_name": None, "cashless_request": False,
        "decision": "REJECTED", "approved_amount": 0.0, "confidence_score": 0.80,
        "rejection_reasons": ["PRE_AUTH_MISSING"], "fraud_flags": [], "deductions": [],
        "policy_sections_referenced": ["coverage_diagnostic"],
        "notes": "MRI requires pre-authorization for claims above ₹10000. No pre-auth found.",
        "next_steps": "Obtain pre-authorization and resubmit.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active. Step 2 (DOCUMENTS): valid. Step 3 (COVERAGE): MRI requires pre-auth above ₹10000; ₹15000 claim has no pre-auth. REJECTED.",
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
        "deductions": [], "policy_sections_referenced": [],
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
        "rejection_reasons": ["SERVICE_NOT_COVERED"], "fraud_flags": [], "deductions": [],
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
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active. Step 2 (DOCUMENTS): valid. Step 3 (COVERAGE): acute bronchitis covered. Network hospital: 20% discount applied. APPROVED.",
        "ground_truth": "APPROVED", "is_correct": True,
    },
    {
        "case_id": "TC011", "case_name": "Annual Limit Exhausted - Rejected",
        "member_id": "EMP011", "member_name": "Nandini Iyer",
        "member_join_date": "2024-01-01", "treatment_date": "2024-11-10",
        "claim_amount": 3500.0, "hospital_name": None, "cashless_request": False,
        "decision": "REJECTED", "approved_amount": 0.0, "confidence_score": 1.00,
        "rejection_reasons": ["ANNUAL_LIMIT_EXCEEDED"], "fraud_flags": [], "deductions": [],
        "policy_sections_referenced": ["limits"],
        "notes": "Member has consumed ₹24,800 of ₹25,000 contract annual limit. Remaining ₹200 is insufficient for ₹3,500 claim.",
        "next_steps": "Annual OPD limit exhausted. No further OPD claims can be processed until policy renewal.",
        "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): policy active. Step 2 (DOCUMENTS): valid. Step 3 (COVERAGE): UTI covered. Step 4 (LIMITS): ytd ₹24,800 + claim ₹3,500 = ₹28,300 exceeds contract annual limit ₹25,000. REJECTED.",
        "ground_truth": "REJECTED", "is_correct": True,
    },
    {
        "case_id": "TC012", "case_name": "Duplicate Claim Submission - Rejected",
        "member_id": "EMP012", "member_name": "Arjun Menon",
        "member_join_date": "2024-01-01", "treatment_date": "2024-10-28",
        "claim_amount": 2200.0, "hospital_name": None, "cashless_request": False,
        "decision": "REJECTED", "approved_amount": 0.0, "confidence_score": 1.00,
        "rejection_reasons": ["DUPLICATE_CLAIM"], "fraud_flags": [], "deductions": [],
        "policy_sections_referenced": ["claim_requirements"],
        "notes": "Claim flagged as duplicate of previously processed claim CLM-20241028-0045 for same member, date, and diagnosis.",
        "next_steps": "If you believe this is an error, contact the claims helpdesk with your original claim reference.",
        "reasoning": "Pre-Step (DUPLICATE): is_duplicate_claim=True, previous_claim_id=CLM-20241028-0045. Immediately REJECTED with DUPLICATE_CLAIM.",
        "ground_truth": "REJECTED", "is_correct": True,
    },
    {
        "case_id": "TC013", "case_name": "Dependent Age Limit Exceeded - Rejected",
        "member_id": "EMP013", "member_name": "Shalini Bose",
        "member_join_date": "2024-01-01", "treatment_date": "2024-11-05",
        "claim_amount": 1800.0, "hospital_name": None, "cashless_request": False,
        "decision": "REJECTED", "approved_amount": 0.0, "confidence_score": 1.00,
        "rejection_reasons": ["DEPENDENT_AGE_EXCEEDED"], "fraud_flags": [], "deductions": [],
        "policy_sections_referenced": ["eligibility"],
        "notes": "Dependent Rohit Bose (age 26) exceeds maximum dependent child age of 25 years under this policy.",
        "next_steps": "Dependent children above age 25 are not covered. Rohit Bose must obtain independent health insurance.",
        "reasoning": "Step 1 (ELIGIBILITY): dependent_age=26 > 25 maximum. Immediately REJECTED with DEPENDENT_AGE_EXCEEDED.",
        "ground_truth": "REJECTED", "is_correct": True,
    },
    {
        "case_id": "TC014", "case_name": "Unregistered Doctor - Rejected",
        "member_id": "EMP014", "member_name": "Pooja Kulkarni",
        "member_join_date": "2024-01-01", "treatment_date": "2024-10-22",
        "claim_amount": 2500.0, "hospital_name": None, "cashless_request": False,
        "decision": "APPROVED", "approved_amount": 2175.0, "confidence_score": 1.00,
        "rejection_reasons": [], "fraud_flags": [],
        "deductions": [{"reason": "10% co-pay on consultation fee", "amount": 325.0}],
        "policy_sections_referenced": ["coverage_consultation"],
        "notes": "Registration MH/99999/2023 is structurally valid (format STATE/NUMBER/YEAR). MCI registry lookup not available — claim approved. Known limitation: #14 in assumptions.",
        "next_steps": "Reimbursement will be credited within 5-7 working days.",
        "reasoning": "Step 2 (DOCUMENTS): doctor reg MH/99999/2023 passes format validation. No MCI registry API available to verify authenticity. Proceeding. APPROVED with co-pay.",
        "ground_truth": "REJECTED", "is_correct": False,
    },
    {
        "case_id": "TC015", "case_name": "OTC Medicines Excluded - Partial Approval",
        "member_id": "EMP015", "member_name": "Girish Pillai",
        "member_join_date": "2024-01-01", "treatment_date": "2024-10-30",
        "claim_amount": 4200.0, "hospital_name": None, "cashless_request": False,
        "decision": "PARTIAL", "approved_amount": 3310.0, "confidence_score": 0.90,
        "rejection_reasons": [], "fraud_flags": [],
        "deductions": [
            {"reason": "Paracetamol 650mg — OTC medicine excluded", "amount": 200.0},
            {"reason": "Antacid syrup — OTC medicine excluded", "amount": 300.0},
            {"reason": "10% co-pay on consultation fee", "amount": 100.0},
            {"reason": "10% co-pay on pharmacy items", "amount": 290.0},
        ],
        "policy_sections_referenced": ["exclusions", "coverage_pharmacy"],
        "notes": "Antibiotic (Azithromycin) and chest X-ray approved. OTC medicines (₹500) excluded. Co-pay applied on covered items.",
        "next_steps": "Partial reimbursement of ₹3,310 will be credited within 5-7 working days.",
        "reasoning": "Step 3 (COVERAGE): Azithromycin covered; Paracetamol and Antacid are OTC — excluded. Step 4 (LIMITS): within per-claim limit. PARTIAL.",
        "ground_truth": "PARTIAL", "is_correct": True,
    },
    {
        "case_id": "TC016", "case_name": "Maternity OPD - Approved After Waiting Period",
        "member_id": "EMP016", "member_name": "Asha Ramachandran",
        "member_join_date": "2024-01-01", "treatment_date": "2024-11-05",
        "claim_amount": 3000.0, "hospital_name": None, "cashless_request": False,
        "decision": "APPROVED", "approved_amount": 3000.0, "confidence_score": 0.90,
        "rejection_reasons": [], "fraud_flags": [], "deductions": [],
        "policy_sections_referenced": ["waiting_periods", "coverage_consultation"],
        "notes": "Member joined 2024-01-01. Maternity waiting period of 270 days was satisfied on 2024-09-28. Treatment date 2024-11-05 is within coverage.",
        "next_steps": "Reimbursement of ₹3,000 will be credited within 5-7 working days.",
        "reasoning": "Step 1 (ELIGIBILITY): treatment_date 2024-11-05 − join_date 2024-01-01 = 308 days > 270-day maternity waiting period. Eligible. APPROVED.",
        "ground_truth": "APPROVED", "is_correct": True,
    },
    {
        "case_id": "TC017", "case_name": "Teleconsultation - Approved",
        "member_id": "EMP017", "member_name": "Kiran Jain",
        "member_join_date": "2024-01-01", "treatment_date": "2024-11-01",
        "claim_amount": 500.0, "hospital_name": None, "cashless_request": False,
        "decision": "APPROVED", "approved_amount": 500.0, "confidence_score": 0.95,
        "rejection_reasons": [], "fraud_flags": [], "deductions": [],
        "policy_sections_referenced": ["coverage_consultation"],
        "notes": "Teleconsultation via registered platform Practo. Within ₹500 per-visit teleconsultation limit. No co-pay applies.",
        "next_steps": "Reimbursement of ₹500 will be credited within 5-7 working days.",
        "reasoning": "Step 3 (COVERAGE): teleconsultation via Practo (registered platform) covered. Step 4 (LIMITS): ₹500 ≤ ₹500 per-visit limit, no co-pay. APPROVED.",
        "ground_truth": "APPROVED", "is_correct": True,
    },
    {
        "case_id": "TC018", "case_name": "Physiotherapy Session Cap Exceeded - Partial Approval",
        "member_id": "EMP018", "member_name": "Rahul Sharma",
        "member_join_date": "2024-01-01", "treatment_date": "2024-10-01",
        "claim_amount": 9000.0, "hospital_name": None, "cashless_request": False,
        "decision": "PARTIAL", "approved_amount": 7200.0, "confidence_score": 0.90,
        "rejection_reasons": [], "fraud_flags": [],
        "deductions": [{"reason": "Sessions 9–10 exceed annual physiotherapy cap of 8 sessions", "amount": 1800.0}],
        "policy_sections_referenced": ["coverage_physiotherapy", "limits"],
        "notes": "8 of 10 physiotherapy sessions approved (₹7,200). Sessions 9 and 10 rejected — annual cap of 8 sessions reached.",
        "next_steps": "Partial reimbursement of ₹7,200 will be credited within 5-7 working days.",
        "reasoning": "Step 3 (COVERAGE): physiotherapy for lumbar spondylosis covered. Step 4 (LIMITS): sessions_claimed=10 > annual_session_cap=8. Approve 8 × ₹900 = ₹7,200. PARTIAL.",
        "ground_truth": "PARTIAL", "is_correct": True,
    },
    {
        "case_id": "TC019", "case_name": "Prescription and Bill Date Mismatch - Manual Review",
        "member_id": "EMP019", "member_name": "Divya Nambiar",
        "member_join_date": "2024-01-01", "treatment_date": "2024-10-10",
        "claim_amount": 4000.0, "hospital_name": None, "cashless_request": False,
        "decision": "MANUAL_REVIEW", "approved_amount": 0.0, "confidence_score": 0.85,
        "rejection_reasons": [],
        "fraud_flags": ["Bill date (2024-10-13) is 3 days after prescription date (2024-10-10) — possible pharmacy pickup delay"],
        "deductions": [],
        "policy_sections_referenced": ["claim_requirements"],
        "notes": "Date gap of 3 days between prescription and pharmacy bill. Consistent with normal pharmacy pickup delay but requires manual verification.",
        "next_steps": "A claims officer will review the date discrepancy within 2-3 business days.",
        "reasoning": "Step 2 (DOCUMENTS): date_gap=3 days (SOFT mismatch). Gap 1–7 days → MANUAL_REVIEW. Routed without proceeding to further steps.",
        "ground_truth": "MANUAL_REVIEW", "is_correct": True,
    },
    {
        "case_id": "TC020", "case_name": "Mental Health Consultation - Approved",
        "member_id": "EMP020", "member_name": "Sunita Rao",
        "member_join_date": "2024-01-01", "treatment_date": "2024-11-08",
        "claim_amount": 2000.0, "hospital_name": None, "cashless_request": False,
        "decision": "APPROVED", "approved_amount": 1800.0, "confidence_score": 0.90,
        "rejection_reasons": [], "fraud_flags": [],
        "deductions": [{"reason": "10% co-pay on psychiatrist consultation fee", "amount": 200.0}],
        "policy_sections_referenced": ["coverage_consultation"],
        "notes": "Mental health OPD covered from policy year 2024 (Mental Healthcare Act 2017). Within ₹2,500 per-visit limit. 10% co-pay applied.",
        "next_steps": "Reimbursement of ₹1,800 will be credited within 5-7 working days.",
        "reasoning": "Step 3 (COVERAGE): psychiatrist consultation covered under mental health OPD from 2024. Step 4 (LIMITS): ₹2,000 within ₹2,500 per-visit limit. APPROVED with 10% co-pay.",
        "ground_truth": "APPROVED", "is_correct": True,
    },
]


@app.function(volumes={VOLUME_MOUNT: volume})
def seed_db():
    """Populate DB with 20 test-case results (TC001–TC020). Safe to re-run."""
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
        for row in _SEED_DATA:
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

            ytd = 24800.0 if row["case_id"] == "TC011" else 0.0
            session.add(Claim(
                id=claim_id, member_id=row["member_id"], member_name=row["member_name"],
                member_join_date=row["member_join_date"], treatment_date=row["treatment_date"],
                claim_amount=row["claim_amount"], hospital_name=row["hospital_name"],
                cashless_request=row["cashless_request"], ytd_claimed_amount=ytd,
                previous_claims_same_day=3 if row["case_id"] == "TC008" else 0,
                status="PROCESSED", test_case_id=row["case_id"], created_at=now,
            ))
            session.add(ClaimDecision(
                claim_id=claim_id, reasoning=row["reasoning"], decision=row["decision"],
                approved_amount=row["approved_amount"],
                rejection_reasons=_json.dumps(row["rejection_reasons"]),
                deductions=_json.dumps(row["deductions"]),
                confidence_score=row["confidence_score"],
                fraud_flags=_json.dumps(row["fraud_flags"]),
                policy_sections_referenced=_json.dumps(row["policy_sections_referenced"]),
                notes=row["notes"], next_steps=row["next_steps"], created_at=now,
            ))
            session.add(EvaluationLog(
                claim_id=claim_id, ai_decision=row["decision"],
                ground_truth_decision=row["ground_truth"], is_correct=row["is_correct"],
                error_type=None, amount_deviation=None, created_at=now,
            ))
            session.commit()
            print(f"  ✓ {claim_id} — {row['decision']}")

    print(f"\nSeeded {len(_SEED_DATA)} test cases into {VOLUME_MOUNT}/claims.db")


@app.function(volumes={VOLUME_MOUNT: volume})
def clear_seed():
    """Rollback: remove only the 20 seeded test-case rows."""
    import os, sys
    sys.path.insert(0, "/app")
    os.environ.setdefault("DATABASE_URL", f"sqlite:////{VOLUME_MOUNT}/claims.db")
    os.environ.setdefault("OPENAI_API_KEY", "placeholder")

    from sqlmodel import Session, select
    from database import engine
    from models import Claim, ClaimDecision, ClaimDocument, EvaluationLog

    with Session(engine) as session:
        for row in _SEED_DATA:
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
