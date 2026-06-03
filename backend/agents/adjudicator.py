import json
from pathlib import Path

from openai import OpenAI

from config import settings
from models import AdjudicationDecision, ClaimSubmission, ExtractionResult
from rag.retriever import build_rag_query, retrieve_policy_context

client = OpenAI(api_key=settings.OPENAI_API_KEY)

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "adjudicator_system.txt"
_system_prompt: str | None = None


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return _system_prompt


def _build_user_message(
    claim_id: str,
    submission: ClaimSubmission,
    extraction: ExtractionResult,
    policy_context: list[str],
) -> str:
    policy_text = "\n\n---\n\n".join(policy_context) if policy_context else "No specific policy context retrieved."

    docs_summary = []
    for doc in extraction.documents:
        docs_summary.append({
            "doc_type": doc.doc_type,
            "doctor_name": doc.doctor_name,
            "doctor_reg": doc.doctor_reg,
            "patient_name": doc.patient_name,
            "diagnosis": doc.diagnosis,
            "medicines": doc.medicines,
            "tests_prescribed": doc.tests_prescribed,
            "procedures": doc.procedures,
            "treatment_date": doc.treatment_date,
            "consultation_fee": doc.consultation_fee,
            "total_amount": doc.total_amount,
            "line_items": [li.model_dump() for li in doc.line_items],
            "extraction_confidence": doc.extraction_confidence,
        })

    return f"""
RETRIEVED POLICY CONTEXT:
{policy_text}

════════════════════════════════════════
CLAIM DETAILS:
════════════════════════════════════════
Claim ID        : {claim_id}
Member ID       : {submission.member_id}
Member Name     : {submission.member_name}
Member Join Date: {submission.member_join_date}
Treatment Date  : {submission.treatment_date}
Claim Amount    : ₹{submission.claim_amount}
YTD Claimed     : ₹{submission.ytd_claimed_amount}
Hospital        : {submission.hospital_name or "Not specified"}
Cashless Request: {submission.cashless_request}
Same-day Claims : {submission.previous_claims_same_day}

════════════════════════════════════════
EXTRACTED DOCUMENT DATA:
════════════════════════════════════════
Merged Diagnosis          : {extraction.merged_diagnosis}
Date Consistent           : {extraction.date_consistent}
Patient Name Consistent   : {extraction.patient_name_consistent}
All Required Docs Present : {extraction.all_required_docs_present}
Missing Docs              : {extraction.missing_docs}

Documents ({len(extraction.documents)} total):
{json.dumps(docs_summary, indent=2)}

════════════════════════════════════════
Apply the adjudication rules from your system prompt.
The claim_id in your response must be exactly: {claim_id}
""".strip()


def adjudicate(
    claim_id: str,
    submission: ClaimSubmission,
    extraction: ExtractionResult,
) -> AdjudicationDecision:
    """Run the full adjudication pipeline for a claim."""

    all_procedures: list[str] = []
    all_medicines: list[str] = []
    for doc in extraction.documents:
        all_procedures.extend(doc.procedures)
        all_medicines.extend(doc.medicines)

    rag_query = build_rag_query(
        diagnosis=extraction.merged_diagnosis,
        procedures=all_procedures,
        medicines=all_medicines,
        doc_types=[d.doc_type for d in extraction.documents],
        hospital=submission.hospital_name,
    )

    policy_context = retrieve_policy_context(rag_query, top_k=5)

    user_message = _build_user_message(claim_id, submission, extraction, policy_context)

    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _get_system_prompt()},
            {"role": "user", "content": user_message},
        ],
        response_format=AdjudicationDecision,
        max_tokens=1500,
    )

    decision = response.choices[0].message.parsed
    # Ensure claim_id is always set correctly (guard against model hallucination)
    decision.claim_id = claim_id
    return decision
