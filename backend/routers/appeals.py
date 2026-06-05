import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import (
    AppealResolution,
    AppealSubmission,
    Claim,
    ClaimAppeal,
    ClaimDecision,
    EvaluationLog,
)

router = APIRouter(tags=["appeals"])


def _now() -> str:
    return datetime.utcnow().isoformat()


# ─── POST /claims/{id}/appeal ────────────────────────────────────────────────


@router.post("/claims/{claim_id}/appeal")
def submit_appeal(
    claim_id: str,
    body: AppealSubmission,
    session: Session = Depends(get_session),
):
    claim = session.get(Claim, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if claim.status not in ("PROCESSED", "ERROR"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot appeal a claim with status '{claim.status}'",
        )

    # Check if there is already a pending appeal
    existing = session.exec(
        select(ClaimAppeal)
        .where(ClaimAppeal.claim_id == claim_id)
        .where(ClaimAppeal.status == "PENDING")
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="An appeal is already pending for this claim")

    appeal = ClaimAppeal(
        claim_id=claim_id,
        appeal_reason=body.appeal_reason,
        additional_notes=body.additional_notes,
        status="PENDING",
        created_at=_now(),
    )
    session.add(appeal)

    claim.status = "UNDER_REVIEW"
    session.add(claim)
    session.commit()
    session.refresh(appeal)

    # Simple coded email — notify admin of new appeal
    from utils.email import get_admin_email, send_simple_email
    admin_email = get_admin_email(session)
    if admin_email:
        decision = session.exec(
            select(ClaimDecision)
            .where(ClaimDecision.claim_id == claim_id)
            .order_by(ClaimDecision.created_at.desc())
        ).first()
        send_simple_email(
            to=admin_email,
            subject=f"[Plum Claims] New Appeal — {claim_id}",
            body=(
                f"A new appeal has been submitted and requires your review.\n\n"
                f"Claim ID      : {claim_id}\n"
                f"Member        : {claim.member_name} ({claim.member_id})\n"
                f"Claim Amount  : ₹{claim.claim_amount:,.0f}\n"
                f"Treatment Date: {claim.treatment_date}\n"
                f"AI Decision   : {decision.decision if decision else 'N/A'}\n\n"
                f"Appeal Reason :\n{body.appeal_reason}\n\n"
                f"Additional Notes:\n{body.additional_notes or 'None'}\n\n"
                f"Please log in to the admin portal to review and resolve this appeal."
            ),
        )

    return {
        "appeal_id": appeal.id,
        "claim_id": claim_id,
        "status": "PENDING",
        "message": "Appeal submitted. A reviewer will assess your claim.",
    }


# ─── GET /appeals ─────────────────────────────────────────────────────────────


@router.get("/appeals")
def list_appeals(
    status: str | None = None,
    session: Session = Depends(get_session),
):
    stmt = select(ClaimAppeal)
    if status:
        stmt = stmt.where(ClaimAppeal.status == status.upper())
    appeals = session.exec(stmt.order_by(ClaimAppeal.created_at.desc())).all()

    results = []
    for a in appeals:
        claim = session.get(Claim, a.claim_id)
        decision = session.exec(
            select(ClaimDecision)
            .where(ClaimDecision.claim_id == a.claim_id)
            .order_by(ClaimDecision.created_at.desc())
        ).first()
        results.append({
            "appeal_id": a.id,
            "claim_id": a.claim_id,
            "member_name": claim.member_name if claim else None,
            "claim_amount": claim.claim_amount if claim else None,
            "ai_decision": decision.decision if decision else None,
            "appeal_reason": a.appeal_reason,
            "additional_notes": a.additional_notes,
            "status": a.status,
            "created_at": a.created_at,
            "resolved_at": a.resolved_at,
        })
    return results


# ─── GET /appeals/{id} ────────────────────────────────────────────────────────


@router.get("/appeals/{appeal_id}")
def get_appeal(appeal_id: int, session: Session = Depends(get_session)):
    appeal = session.get(ClaimAppeal, appeal_id)
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found")

    claim = session.get(Claim, appeal.claim_id)
    decision = session.exec(
        select(ClaimDecision)
        .where(ClaimDecision.claim_id == appeal.claim_id)
        .order_by(ClaimDecision.created_at.desc())
    ).first()

    return {
        "appeal": appeal.model_dump(),
        "claim": claim.model_dump() if claim else None,
        "ai_decision": {
            "decision": decision.decision,
            "approved_amount": decision.approved_amount,
            "rejection_reasons": json.loads(decision.rejection_reasons),
            "notes": decision.notes,
        } if decision else None,
    }


# ─── PATCH /appeals/{id}/resolve ──────────────────────────────────────────────


@router.patch("/appeals/{appeal_id}/resolve")
def resolve_appeal(
    appeal_id: int,
    body: AppealResolution,
    session: Session = Depends(get_session),
):
    appeal = session.get(ClaimAppeal, appeal_id)
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found")

    if appeal.status not in ("PENDING", "UNDER_REVIEW"):
        raise HTTPException(
            status_code=400,
            detail=f"Appeal is already resolved (status: {appeal.status})",
        )

    is_upheld = body.new_decision != "REJECTED"

    # Update appeal record
    appeal.status = "UPHELD" if is_upheld else "DISMISSED"
    appeal.reviewer_notes = body.reviewer_notes
    appeal.resolved_at = _now()
    session.add(appeal)

    # If upheld: create a new ClaimDecision with the reviewer's decision
    if is_upheld:
        new_decision = ClaimDecision(
            claim_id=appeal.claim_id,
            reasoning=f"Appeal upheld by reviewer. Original AI decision overridden. {body.reviewer_notes}",
            decision=body.new_decision,
            approved_amount=body.approved_amount,
            rejection_reasons=json.dumps([]),
            deductions=json.dumps([]),
            confidence_score=1.0,
            fraud_flags=json.dumps([]),
            policy_sections_referenced=json.dumps([]),
            notes=f"Appeal upheld by reviewer. {body.reviewer_notes}",
            next_steps="Reimbursement will be processed based on the reviewed decision.",
            created_at=_now(),
        )
        session.add(new_decision)

    # Update claim status
    claim = session.get(Claim, appeal.claim_id)
    if claim:
        claim.status = "PROCESSED"
        session.add(claim)

    # Update evaluation log
    eval_log = session.exec(
        select(EvaluationLog).where(EvaluationLog.claim_id == appeal.claim_id)
    ).first()
    if eval_log:
        eval_log.ground_truth_decision = body.new_decision
        eval_log.is_correct = eval_log.ai_decision == body.new_decision
        if not eval_log.is_correct:
            eval_log.error_type = "FALSE_POSITIVE" if eval_log.ai_decision == "APPROVED" else "FALSE_NEGATIVE"
        session.add(eval_log)

    session.commit()

    return {
        "appeal_id": appeal_id,
        "status": appeal.status,
        "new_decision": body.new_decision if is_upheld else None,
        "message": "Appeal resolved successfully.",
    }
