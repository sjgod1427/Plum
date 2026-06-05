import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from agents.adjudicator import adjudicate
from agents.extractor import extract_document, merge_extractions
from config import settings
from database import get_session
from models import (
    Claim,
    ClaimDecision,
    ClaimDocument,
    ClaimSubmission,
    DirectClaimRequest,
    EvaluationLog,
    ExtractionResult,
)

router = APIRouter(prefix="/claims", tags=["claims"])


def _new_claim_id() -> str:
    return "CLM_" + uuid.uuid4().hex[:8].upper()


def _now() -> str:
    return datetime.utcnow().isoformat()


def _save_decision(session: Session, decision, extraction: ExtractionResult, claim_id: str):
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

    el = EvaluationLog(
        claim_id=claim_id,
        ai_decision=decision.decision,
        created_at=_now(),
    )
    session.add(el)
    session.commit()


# ─── POST /claims ─────────────────────────────────────────────────────────────


@router.post("")
def submit_claim(
    files: list[UploadFile] = File(...),
    data: str = Form(...),
    session: Session = Depends(get_session),
):
    try:
        submission = ClaimSubmission.model_validate_json(data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid claim data: {e}")

    # Auto-enrich session cap from policy when user provides sessions_claimed
    if submission.sessions_claimed and submission.annual_session_cap is None:
        try:
            import json as _json
            with open(settings.POLICY_TERMS_PATH) as _f:
                _policy = _json.load(_f)
            _cap = _policy.get("coverage_details", {}).get("physiotherapy", {}).get("max_sessions_per_year", 8)
            submission = submission.model_copy(update={"annual_session_cap": int(_cap)})
        except Exception:
            submission = submission.model_copy(update={"annual_session_cap": 8})

    claim_id = _new_claim_id()
    upload_dir = Path(settings.UPLOAD_DIR) / claim_id
    upload_dir.mkdir(parents=True, exist_ok=True)

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
        created_at=_now(),
    )
    session.add(claim)
    session.commit()

    try:
        # Save files and extract
        extracted_docs = []
        for file in files:
            if file.filename:
                file_path = upload_dir / file.filename
            else:
                ext = ".pdf" if (file.content_type or "").startswith("application/pdf") else ".jpg"
                file_path = upload_dir / f"doc_{len(extracted_docs)}{ext}"
            contents = file.file.read()
            with open(file_path, "wb") as f:
                f.write(contents)

            doc = extract_document(str(file_path))
            extracted_docs.append(doc)

            session.add(ClaimDocument(
                claim_id=claim_id,
                doc_type=doc.doc_type,
                file_path=str(file_path),
                extracted_data=doc.model_dump_json(),
                created_at=_now(),
            ))
        session.commit()

        extraction = merge_extractions(
            extracted_docs,
            submission.member_name,
            submission.treatment_date,
            submission.claim_amount,
        )

        from utils.email import get_admin_email
        decision = adjudicate(claim_id, submission, extraction, admin_email=get_admin_email(session))

        _save_decision(session, decision, extraction, claim_id)
        claim.status = "PROCESSED"
        session.add(claim)
        session.commit()

        return _claim_response(claim_id, decision, extraction)

    except Exception as e:
        claim.status = "ERROR"
        session.add(claim)
        session.commit()
        raise HTTPException(status_code=500, detail=str(e))


# ─── POST /claims/direct (test suite / API integration) ───────────────────────


@router.post("/direct")
def submit_direct_claim(
    body: DirectClaimRequest,
    session: Session = Depends(get_session),
):
    """Submit a claim with pre-provided extraction — skips document upload."""
    claim_id = _new_claim_id()
    submission = body.submission
    extraction = body.extraction

    # Auto-enrich session cap from policy when caller provides sessions_claimed but not the cap
    if submission.sessions_claimed and submission.annual_session_cap is None:
        try:
            import json as _json
            with open(settings.POLICY_TERMS_PATH) as _f:
                _policy = _json.load(_f)
            _cap = _policy.get("coverage_details", {}).get("physiotherapy", {}).get("max_sessions_per_year", 8)
            submission = submission.model_copy(update={"annual_session_cap": int(_cap)})
        except Exception:
            submission = submission.model_copy(update={"annual_session_cap": 8})

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
        created_at=_now(),
    )
    session.add(claim)
    session.commit()

    try:
        from utils.email import get_admin_email
        decision = adjudicate(claim_id, submission, extraction, admin_email=get_admin_email(session))
        _save_decision(session, decision, extraction, claim_id)
        claim.status = "PROCESSED"
        session.add(claim)
        session.commit()
        return _claim_response(claim_id, decision, extraction)

    except Exception as e:
        claim.status = "ERROR"
        session.add(claim)
        session.commit()
        raise HTTPException(status_code=500, detail=str(e))


# ─── GET /claims ──────────────────────────────────────────────────────────────


@router.get("")
def list_claims(
    status: str | None = None,
    session: Session = Depends(get_session),
):
    stmt = select(Claim)
    if status:
        stmt = stmt.where(Claim.status == status.upper())
    claims = session.exec(stmt.order_by(Claim.created_at.desc())).all()

    results = []
    for c in claims:
        decision = session.exec(
            select(ClaimDecision).where(ClaimDecision.claim_id == c.id).order_by(ClaimDecision.created_at.desc())
        ).first()
        results.append({
            "claim_id": c.id,
            "member_name": c.member_name,
            "treatment_date": c.treatment_date,
            "claim_amount": c.claim_amount,
            "status": c.status,
            "decision": decision.decision if decision else None,
            "approved_amount": decision.approved_amount if decision else None,
            "confidence_score": decision.confidence_score if decision else None,
            "created_at": c.created_at,
        })
    return results


# ─── GET /claims/{id} ────────────────────────────────────────────────────────


@router.get("/{claim_id}")
def get_claim(claim_id: str, session: Session = Depends(get_session)):
    claim = session.get(Claim, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim_id).order_by(ClaimDecision.created_at.desc())
    ).first()

    docs = session.exec(
        select(ClaimDocument).where(ClaimDocument.claim_id == claim_id)
    ).all()

    return {
        "claim": claim.model_dump(),
        "decision": _serialise_decision(decision) if decision else None,
        "documents": [
            {**d.model_dump(), "extracted_data": json.loads(d.extracted_data)}
            for d in docs
        ],
    }


# ─── GET /claims/{id}/decision ────────────────────────────────────────────────


@router.get("/{claim_id}/decision")
def get_decision(claim_id: str, session: Session = Depends(get_session)):
    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim_id).order_by(ClaimDecision.created_at.desc())
    ).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return _serialise_decision(decision)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _serialise_decision(d: ClaimDecision) -> dict:
    return {
        "claim_id": d.claim_id,
        "reasoning": d.reasoning,
        "decision": d.decision,
        "approved_amount": d.approved_amount,
        "rejection_reasons": json.loads(d.rejection_reasons),
        "deductions": json.loads(d.deductions),
        "confidence_score": d.confidence_score,
        "fraud_flags": json.loads(d.fraud_flags),
        "policy_sections_referenced": json.loads(d.policy_sections_referenced),
        "notes": d.notes,
        "next_steps": d.next_steps,
        "created_at": d.created_at,
    }


def _claim_response(claim_id: str, decision, extraction: ExtractionResult) -> dict:
    return {
        "claim_id": claim_id,
        "status": "PROCESSED",
        "decision": {
            "reasoning": decision.reasoning,
            "decision": decision.decision,
            "approved_amount": decision.approved_amount,
            "rejection_reasons": decision.rejection_reasons,
            "deductions": [d.model_dump() for d in decision.deductions],
            "confidence_score": decision.confidence_score,
            "fraud_flags": decision.fraud_flags,
            "policy_sections_referenced": decision.policy_sections_referenced,
            "notes": decision.notes,
            "next_steps": decision.next_steps,
        },
        "extracted_data": {
            "merged_diagnosis": extraction.merged_diagnosis,
            "merged_total": extraction.merged_total,
            "all_required_docs_present": extraction.all_required_docs_present,
            "missing_docs": extraction.missing_docs,
            "date_consistent": extraction.date_consistent,
            "patient_name_consistent": extraction.patient_name_consistent,
        },
    }
