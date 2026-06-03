import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from config import settings
from database import get_session
from models import (
    Claim,
    ClaimDecision,
    ClaimDocument,
    EvaluationLog,
    MetricsLabel,
    PolicyConfig,
    PolicySectionUpdate,
    DirectClaimRequest,
    ClaimSubmission,
    ExtractionResult,
    ExtractedDocument,
    LineItem,
)
from rag.ingest import ingest_policy, ingest_section, rebuild_from_db

router = APIRouter(prefix="/admin", tags=["admin"])

_SECTION_LABELS = {
    "limits": "Coverage Limits",
    "coverage_consultation": "Consultation Fee Coverage",
    "coverage_diagnostic": "Diagnostic Tests Coverage",
    "coverage_pharmacy": "Pharmacy / Medicines Coverage",
    "coverage_dental": "Dental Treatment Coverage",
    "coverage_vision": "Vision / Eye Care Coverage",
    "coverage_alternative": "Alternative Medicine Coverage",
    "waiting_periods": "Waiting Periods",
    "exclusions": "Policy Exclusions",
    "network_hospitals": "Network Hospitals & Cashless",
    "claim_requirements": "Claim Submission Requirements",
}


def _now() -> str:
    return datetime.utcnow().isoformat()


# ─── GET /admin/policy ────────────────────────────────────────────────────────


@router.get("/policy")
def get_policy(session: Session = Depends(get_session)):
    configs = session.exec(select(PolicyConfig)).all()

    if not configs:
        # Fall back to loading from the source file
        try:
            with open(settings.POLICY_TERMS_PATH) as f:
                raw = json.load(f)
            return {"source": "file", "policy": raw}
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Policy file not found")

    policy: dict = {}
    for c in configs:
        policy[c.section] = json.loads(c.config_json)
    return {"source": "database", "policy": policy}


# ─── PATCH /admin/policy/{section} ───────────────────────────────────────────


@router.patch("/policy/{section}")
def update_policy_section(
    section: str,
    body: PolicySectionUpdate,
    session: Session = Depends(get_session),
):
    if section not in _SECTION_LABELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown section '{section}'. Valid sections: {list(_SECTION_LABELS.keys())}",
        )

    existing = session.exec(
        select(PolicyConfig).where(PolicyConfig.section == section)
    ).first()

    if existing:
        existing.config_json = json.dumps(body.config)
        existing.updated_at = _now()
        existing.updated_by = body.updated_by
        session.add(existing)
    else:
        session.add(PolicyConfig(
            section=section,
            config_json=json.dumps(body.config),
            updated_at=_now(),
            updated_by=body.updated_by,
        ))
    session.commit()

    # Re-embed this section in ChromaDB
    ingest_section(section, _SECTION_LABELS[section], body.config)

    return {"section": section, "status": "updated", "rag_synced": True}


# ─── POST /admin/policy/rebuild-rag ──────────────────────────────────────────


@router.post("/policy/rebuild-rag")
def rebuild_rag(session: Session = Depends(get_session)):
    configs = session.exec(select(PolicyConfig)).all()

    if configs:
        sections = [{"section": c.section, "config_json": c.config_json} for c in configs]
        rebuild_from_db(sections)
        return {"status": "rebuilt", "sections": len(sections), "source": "database"}
    else:
        ingest_policy(force=True)
        return {"status": "rebuilt", "source": "policy_terms.json"}


# ─── GET /admin/metrics ───────────────────────────────────────────────────────


@router.get("/metrics")
def get_metrics(session: Session = Depends(get_session)):
    test_cases = _get_test_cases()
    case_map = {tc["case_id"]: tc for tc in test_cases}

    per_case = []
    for tc in test_cases:
        claim_id = f"CLM_{tc['case_id']}"
        eval_log = session.exec(
            select(EvaluationLog).where(EvaluationLog.claim_id == claim_id)
        ).first()
        decision_row = session.exec(
            select(ClaimDecision).where(ClaimDecision.claim_id == claim_id)
        ).first()

        per_case.append({
            "case_id": tc["case_id"],
            "case_name": tc["case_name"],
            "description": tc.get("description", ""),
            "claim_id": claim_id,
            "ground_truth": tc["expected_output"]["decision"],
            "expected_amount": tc["expected_output"].get("approved_amount"),
            "ai_decision": eval_log.ai_decision if eval_log else None,
            "ai_amount": decision_row.approved_amount if decision_row else None,
            "confidence_score": decision_row.confidence_score if decision_row else None,
            "is_correct": eval_log.is_correct if eval_log else None,
            "reasoning": decision_row.reasoning if decision_row else None,
            "notes": decision_row.notes if decision_row else None,
            "rejection_reasons": json.loads(decision_row.rejection_reasons) if decision_row else [],
        })

    labelled = [c for c in per_case if c["is_correct"] is not None]
    total = len(labelled)
    passed = sum(1 for c in labelled if c["is_correct"])

    accuracy = round(passed / total, 4) if total > 0 else None

    tp = sum(1 for c in labelled if c["is_correct"] and c["ai_decision"] == "APPROVED")
    fp = sum(1 for c in labelled if not c["is_correct"] and c["ai_decision"] == "APPROVED")
    fn = sum(1 for c in labelled if not c["is_correct"] and c["ai_decision"] != "APPROVED")
    tn = sum(1 for c in labelled if c["is_correct"] and c["ai_decision"] != "APPROVED")

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else None
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else None
    fpr = round(fp / (fp + tn), 4) if (fp + tn) > 0 else None
    fnr = round(fn / (fn + tp), 4) if (fn + tp) > 0 else None

    deviations = [
        abs(c["ai_amount"] - c["expected_amount"])
        for c in labelled
        if c["ai_amount"] is not None and c["expected_amount"] is not None
    ]
    mean_dev = round(sum(deviations) / len(deviations), 2) if deviations else None

    return {
        "total_test_cases": len(test_cases),
        "evaluated": total,
        "passed": passed,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
        "mean_amount_deviation": mean_dev,
        "data_source": "Plum-provided test_cases.json (10 cases with known expected outputs)",
        "per_case": per_case,
    }


# ─── POST /admin/metrics/run-test-suite ──────────────────────────────────────


@router.post("/metrics/run-test-suite")
def run_test_suite(session: Session = Depends(get_session)):
    """
    Run all 10 Plum-provided test cases.
    - Fixed claim IDs: CLM_TC001 … CLM_TC010 (upsert — always exactly 10 records)
    - Ground truth = expected_output.decision from test_cases.json (not AI answer)
    - Metrics are computed by comparing AI decision vs ground truth
    """
    from agents.adjudicator import adjudicate

    test_cases = _get_test_cases()
    results = []

    print("\n" + "=" * 60)
    print("  TEST SUITE — 10 cases (fixed IDs, upsert)")
    print("=" * 60)

    for i, tc in enumerate(test_cases, 1):
        claim_id = f"CLM_{tc['case_id']}"
        print(f"\n[{i}/10] {claim_id} — {tc['case_name']}")

        try:
            payload = _build_direct_request(tc)
            submission = ClaimSubmission(**payload["submission"])

            raw_ext = payload["extraction"]
            docs = []
            for d in raw_ext["documents"]:
                line_items = [LineItem(**li) for li in d.get("line_items", [])]
                docs.append(ExtractedDocument(**{**d, "line_items": line_items}))

            extraction = ExtractionResult(**{**raw_ext, "documents": docs})

            print(f"  → diagnosis: {extraction.merged_diagnosis}  amount: ₹{submission.claim_amount}")

            # ── Delete existing records for this fixed claim ID ──────────────
            _delete_test_claim(session, claim_id)

            # ── Create claim record ──────────────────────────────────────────
            claim = Claim(
                id=claim_id,
                member_id=submission.member_id,
                member_name=submission.member_name,
                member_join_date=submission.member_join_date,
                treatment_date=submission.treatment_date,
                claim_amount=submission.claim_amount,
                hospital_name=submission.hospital_name,
                cashless_request=submission.cashless_request,
                ytd_claimed_amount=submission.ytd_claimed_amount,
                previous_claims_same_day=submission.previous_claims_same_day,
                status="PENDING",
                test_case_id=tc["case_id"],
                created_at=_now(),
            )
            session.add(claim)
            session.commit()

            # ── Run adjudication ─────────────────────────────────────────────
            decision = adjudicate(claim_id, submission, extraction)

            # ── Save ClaimDecision ───────────────────────────────────────────
            cd = ClaimDecision(
                claim_id=claim_id,
                reasoning=decision.reasoning,
                decision=decision.decision,
                approved_amount=decision.approved_amount,
                rejection_reasons=json.dumps(decision.rejection_reasons),
                deductions=json.dumps([d.model_dump() for d in decision.deductions]),
                confidence_score=decision.confidence_score,
                fraud_flags=json.dumps(decision.fraud_flags),
                policy_sections_referenced=json.dumps(decision.policy_sections_referenced),
                notes=decision.notes,
                next_steps=decision.next_steps,
                created_at=_now(),
            )
            session.add(cd)

            # ── Save EvaluationLog with ground truth ─────────────────────────
            ground_truth = tc["expected_output"]["decision"]
            is_correct = decision.decision == ground_truth
            error_type = None
            if not is_correct:
                error_type = "FALSE_POSITIVE" if decision.decision == "APPROVED" else "FALSE_NEGATIVE"

            expected_amount = tc["expected_output"].get("approved_amount")
            amount_dev = None
            if expected_amount is not None:
                amount_dev = abs(decision.approved_amount - expected_amount)

            el = EvaluationLog(
                claim_id=claim_id,
                ai_decision=decision.decision,
                ground_truth_decision=ground_truth,
                is_correct=is_correct,
                error_type=error_type,
                amount_deviation=amount_dev,
                created_at=_now(),
            )
            session.add(el)

            claim.status = "PROCESSED"
            session.add(claim)
            session.commit()

            icon = "✓" if is_correct else "✗"
            print(f"  {icon} ground_truth={ground_truth}  ai={decision.decision}  amount=₹{decision.approved_amount}  conf={decision.confidence_score:.2f}")
            if not is_correct:
                print(f"  REASONING: {decision.reasoning[:300]}")

            results.append({
                "case_id": tc["case_id"],
                "case_name": tc["case_name"],
                "passed": is_correct,
                "ground_truth": ground_truth,
                "ai_decision": decision.decision,
                "expected_amount": expected_amount,
                "actual_amount": decision.approved_amount,
                "confidence_score": decision.confidence_score,
                "claim_id": claim_id,
            })

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results.append({
                "case_id": tc["case_id"],
                "case_name": tc["case_name"],
                "passed": False,
                "error": str(e),
            })

    passed_count = sum(1 for r in results if r.get("passed"))
    print(f"\n{'=' * 60}")
    print(f"  RESULT: {passed_count}/{len(results)} passed")
    print("=" * 60 + "\n")

    return {
        "total": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "results": results,
        "run_at": _now(),
    }


def _delete_test_claim(session: Session, claim_id: str):
    """Delete all DB records for a test claim so we can upsert cleanly."""
    for row in session.exec(select(ClaimDecision).where(ClaimDecision.claim_id == claim_id)).all():
        session.delete(row)
    for row in session.exec(select(EvaluationLog).where(EvaluationLog.claim_id == claim_id)).all():
        session.delete(row)
    for row in session.exec(select(ClaimDocument).where(ClaimDocument.claim_id == claim_id)).all():
        session.delete(row)
    existing = session.get(Claim, claim_id)
    if existing:
        session.delete(existing)
    session.commit()


# ─── PATCH /admin/metrics/{claim_id}/label ───────────────────────────────────


@router.patch("/metrics/{claim_id}/label")
def label_claim(
    claim_id: str,
    body: MetricsLabel,
    session: Session = Depends(get_session),
):
    log = session.exec(
        select(EvaluationLog).where(EvaluationLog.claim_id == claim_id)
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="No evaluation log for this claim")

    decision_row = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim_id)
    ).first()

    log.ground_truth_decision = body.ground_truth_decision
    log.is_correct = log.ai_decision == body.ground_truth_decision

    if not log.is_correct:
        log.error_type = (
            "FALSE_POSITIVE" if log.ai_decision == "APPROVED" else "FALSE_NEGATIVE"
        )

    if body.actual_approved_amount is not None and decision_row:
        log.amount_deviation = abs(decision_row.approved_amount - body.actual_approved_amount)

    session.add(log)
    session.commit()

    return {
        "claim_id": claim_id,
        "is_correct": log.is_correct,
        "error_type": log.error_type,
    }


# ─── Test suite helpers ───────────────────────────────────────────────────────


def _get_test_cases() -> list[dict]:
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "test_cases.json")
    with open(os.path.abspath(path)) as f:
        return json.load(f)["test_cases"]


def _build_direct_request(tc: dict) -> dict:
    docs = tc.get("input_data", {}).get("documents", {})
    rx = docs.get("prescription", {})
    bill = docs.get("bill", {})
    input_data = tc.get("input_data", {})

    extracted_docs = []

    if rx:
        medicines = rx.get("medicines_prescribed", [])
        # "treatment" key used in some test cases (e.g. TC006 Ayurveda, TC009 obesity)
        raw_treatment = rx.get("treatment")
        procedures = rx.get("procedures", [])
        if raw_treatment and raw_treatment not in procedures:
            procedures = [raw_treatment] + procedures
        tests = rx.get("tests_prescribed", [])
        extracted_docs.append({
            "doc_type": "prescription",
            "doctor_name": rx.get("doctor_name"),
            "doctor_reg": rx.get("doctor_reg"),
            "patient_name": input_data.get("member_name"),
            "diagnosis": rx.get("diagnosis"),
            "medicines": medicines,
            "tests_prescribed": tests,
            "procedures": procedures,
            "treatment_date": input_data.get("treatment_date"),
            "consultation_fee": bill.get("consultation_fee"),
            "total_amount": input_data.get("claim_amount"),
            "line_items": [],
            "extraction_confidence": 0.95,
        })

    if bill:
        line_items = [
            {"description": k, "amount": v}
            for k, v in bill.items()
            if isinstance(v, (int, float))
        ]
        extracted_docs.append({
            "doc_type": "bill",
            "doctor_name": None,
            "doctor_reg": None,
            "patient_name": input_data.get("member_name"),
            "diagnosis": None,
            "medicines": [],
            "tests_prescribed": [],
            "procedures": [],
            "treatment_date": input_data.get("treatment_date"),
            "consultation_fee": bill.get("consultation_fee"),
            "total_amount": input_data.get("claim_amount"),
            "line_items": line_items,
            "extraction_confidence": 0.95,
        })

    return {
        "submission": {
            "member_id": input_data.get("member_id", "EMP_TEST"),
            "member_name": input_data.get("member_name", "Test User"),
            "member_join_date": input_data.get("member_join_date", "2024-01-01"),
            "treatment_date": input_data.get("treatment_date", "2024-10-01"),
            "claim_amount": float(input_data.get("claim_amount", 0)),
            "hospital_name": input_data.get("hospital"),
            "cashless_request": input_data.get("cashless_request", False),
            "ytd_claimed_amount": 0.0,
            "previous_claims_same_day": input_data.get("previous_claims_same_day", 0),
        },
        "extraction": {
            "documents": extracted_docs,
            "merged_diagnosis": (rx.get("diagnosis") or rx.get("treatment") or "Unknown"),
            "merged_total": float(input_data.get("claim_amount", 0)),
            "date_consistent": True,
            "patient_name_consistent": True,
            "all_required_docs_present": bool(rx),
            "missing_docs": [] if rx else ["Prescription from registered doctor"],
        },
    }
