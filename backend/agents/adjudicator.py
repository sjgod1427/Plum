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


def _send_manual_review_agentic_email(
    admin_email: str,
    claim_id: str,
    submission: ClaimSubmission,
    extraction: ExtractionResult,
    decision: AdjudicationDecision,
) -> None:
    """
    Agentic workflow — ACTIVE: OpenAI Agents SDK
    The agent receives full claim context, drafts the email, and calls
    send_notification_email tool autonomously.

    Commented below: previous manual tool-calling approach (raw OpenAI SDK).
    """

    # ── APPROACH: Raw OpenAI SDK tool calling ← ACTIVE ───────────────────────
    # Note: openai-agents SDK approach is commented below — blocked by naming
    # conflict between our local agents/ directory and the openai-agents package.
    # Will be resolved by renaming agents/ → claim_agents/ in a future iteration.

    prompt = f"""
A claim has been flagged for MANUAL REVIEW. Draft and send a notification email.

Claim ID       : {claim_id}
Member         : {submission.member_name} ({submission.member_id})
Treatment Date : {submission.treatment_date}
Claim Amount   : ₹{submission.claim_amount:,.0f}
Hospital       : {submission.hospital_name or "Not specified"}
Diagnosis      : {extraction.merged_diagnosis}
Fraud Flags    : {decision.fraud_flags}
Confidence     : {decision.confidence_score:.0%}
Reasoning      : {decision.reasoning[:600]}
Notes          : {decision.notes}

Use the send_email tool to send the notification now.
"""

    tools = [
        {
            "type": "function",
            "function": {
                "name": "send_email",
                "description": "Send a manual review notification email to the admin reviewer",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string", "description": "Email subject line"},
                        "body":    {"type": "string", "description": "Plain text email body"},
                    },
                    "required": ["subject", "body"],
                },
            },
        }
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # cheaper — email drafting doesn't need GPT-4o
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a claims notification agent for Plum Insurance. "
                        "Draft professional, concise alert emails for claims requiring manual review. "
                        "Write in plain text only — no markdown, no asterisks, no hashtags, no bullet dashes. "
                        "Use simple line breaks and spacing for structure. "
                        "Always call the send_email tool — never respond with plain text only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "send_email"}},
        )
        tool_call = response.choices[0].message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        from utils.email import send_simple_email
        sent = send_simple_email(to=admin_email, subject=args["subject"], body=args["body"])
        if sent:
            print(f"[Adjudicator] Agentic MANUAL_REVIEW email sent to {admin_email}")
        else:
            print(f"[Adjudicator] Email send failed — check SendGrid config")
    except Exception as e:
        print(f"[Adjudicator] Agentic email error: {e}")

    # ── APPROACH: OpenAI Agents SDK (pending agents/ → claim_agents/ rename) ──
    # import asyncio
    # from agents import Agent, Runner, function_tool  # conflicts with local agents/
    # from utils.email import send_simple_email
    # @function_tool
    # def send_notification_email(subject: str, body: str) -> str:
    #     """Send a MANUAL_REVIEW notification email to the admin reviewer."""
    #     result = send_simple_email(to=admin_email, subject=subject, body=body)
    #     return "Email sent successfully." if result else "Email send failed."
    # agent = Agent(
    #     name="ClaimsNotifier", model="gpt-4o-mini",
    #     instructions="Draft and send professional MANUAL_REVIEW alert emails. Always call the tool.",
    #     tools=[send_notification_email],
    # )
    # try:
    #     asyncio.run(Runner.run(agent, prompt))
    #     print(f"[Adjudicator] Agentic email sent to {admin_email}")
    # except Exception as e:
    #     print(f"[Adjudicator] Agentic email error: {e}")


def adjudicate(
    claim_id: str,
    submission: ClaimSubmission,
    extraction: ExtractionResult,
    admin_email: str | None = None,  # if set, sends agentic email on MANUAL_REVIEW
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
        model="gpt-4o",       # Approach A: GPT-4o — 10/10 passing          ← ACTIVE
        # model="gpt-4o-mini", # Approach B: mini — 9/10, fails TC002 + TC010 amounts
        messages=[
            {"role": "system", "content": _get_system_prompt()},
            {"role": "user", "content": user_message},
        ],
        response_format=AdjudicationDecision,
        max_tokens=1500,
    )

    decision = response.choices[0].message.parsed
    decision.claim_id = claim_id

    # Agentic email — only on MANUAL_REVIEW and only if admin email is configured
    if decision.decision == "MANUAL_REVIEW" and admin_email:
        _send_manual_review_agentic_email(admin_email, claim_id, submission, extraction, decision)

    return decision
