from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, Float, Boolean, Text
from sqlmodel import SQLModel, Field


# ─── OpenAI Structured Output Models ─────────────────────────────────────────
# Note: All fields that may be null are Optional without defaults so they
# appear in the JSON schema's `required` array (OpenAI strict mode requirement).


class LineItem(BaseModel):
    description: str
    amount: float


class ExtractedDocument(BaseModel):
    """Returned by GPT-4o Vision for each uploaded document."""
    doc_type: Literal["prescription", "bill", "diagnostic_report", "pharmacy_bill"]
    doctor_name: Optional[str]
    doctor_reg: Optional[str]
    patient_name: Optional[str]
    diagnosis: Optional[str]
    medicines: list[str]
    tests_prescribed: list[str]
    procedures: list[str]
    treatment_date: Optional[str]       # "YYYY-MM-DD" string
    consultation_fee: Optional[float]
    total_amount: Optional[float]
    line_items: list[LineItem]
    extraction_confidence: float        # 0.0 – 1.0


class ExtractionResult(BaseModel):
    """Merged result across all documents for a single claim."""
    documents: list[ExtractedDocument]
    merged_diagnosis: str
    merged_total: float
    date_consistent: bool
    patient_name_consistent: bool
    all_required_docs_present: bool
    missing_docs: list[str]


class Deduction(BaseModel):
    reason: str
    amount: float


class AdjudicationDecision(BaseModel):
    """Returned by the adjudication agent — structured output from GPT-4o."""
    claim_id: str
    reasoning: str                      # step-by-step chain-of-thought before the decision
    decision: Literal["APPROVED", "REJECTED", "PARTIAL", "MANUAL_REVIEW"]
    approved_amount: float
    rejection_reasons: list[str]
    deductions: list[Deduction]
    confidence_score: float             # 0.0 – 1.0
    fraud_flags: list[str]
    policy_sections_referenced: list[str]
    notes: str
    next_steps: str


# ─── API Request / Response Models ───────────────────────────────────────────


class ClaimSubmission(BaseModel):
    member_id: str
    member_name: str
    member_join_date: str               # "YYYY-MM-DD"
    treatment_date: str                 # "YYYY-MM-DD"
    claim_amount: float
    hospital_name: Optional[str] = None
    cashless_request: bool = False
    ytd_claimed_amount: float = 0.0
    previous_claims_same_day: int = 0
    annual_limit_total: Optional[float] = None   # per-contract override; defaults to policy (₹50,000)
    dependent_name: Optional[str] = None
    dependent_age: Optional[int] = None
    dependent_relation: Optional[str] = None
    is_duplicate_claim: bool = False
    previous_claim_id: Optional[str] = None
    sessions_claimed: Optional[int] = None
    annual_session_cap: Optional[int] = None


class DirectClaimRequest(BaseModel):
    """Submit a claim with pre-provided extraction (skips document upload — used by test suite)."""
    submission: ClaimSubmission
    extraction: ExtractionResult


class AppealSubmission(BaseModel):
    appeal_reason: str
    additional_notes: Optional[str] = None


class AppealResolution(BaseModel):
    new_decision: Literal["APPROVED", "REJECTED", "PARTIAL"]
    approved_amount: float
    reviewer_notes: str


class PolicySectionUpdate(BaseModel):
    config: dict
    updated_by: str = "admin"


class MetricsLabel(BaseModel):
    ground_truth_decision: Literal["APPROVED", "REJECTED", "PARTIAL", "MANUAL_REVIEW"]
    actual_approved_amount: Optional[float] = None


# ─── Database Tables (SQLModel) ───────────────────────────────────────────────
# JSON array/object columns are stored as TEXT strings; helpers on the router
# layer handle serialisation.


class Claim(SQLModel, table=True):
    id: str = Field(sa_column=Column(String, primary_key=True))
    member_id: str = Field(sa_column=Column(String, nullable=False))
    member_name: str = Field(sa_column=Column(String, nullable=False))
    member_join_date: str = Field(sa_column=Column(String, nullable=False))
    treatment_date: str = Field(sa_column=Column(String, nullable=False))
    claim_amount: float = Field(sa_column=Column(Float, nullable=False))
    hospital_name: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    cashless_request: bool = Field(default=False, sa_column=Column(Boolean, default=False))
    ytd_claimed_amount: float = Field(default=0.0, sa_column=Column(Float, default=0.0))
    previous_claims_same_day: int = Field(default=0, sa_column=Column(Integer, default=0))
    status: str = Field(default="PENDING", sa_column=Column(String, default="PENDING"))
    test_case_id: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    created_at: str = Field(sa_column=Column(String, nullable=False))


class ClaimDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, sa_column=Column(Integer, primary_key=True, autoincrement=True))
    claim_id: str = Field(sa_column=Column(String, nullable=False))
    doc_type: str = Field(sa_column=Column(String, nullable=False))
    file_path: str = Field(sa_column=Column(String, nullable=False))
    extracted_data: str = Field(sa_column=Column(Text, nullable=False))
    created_at: str = Field(sa_column=Column(String, nullable=False))


class ClaimDecision(SQLModel, table=True):
    id: Optional[int] = Field(default=None, sa_column=Column(Integer, primary_key=True, autoincrement=True))
    claim_id: str = Field(sa_column=Column(String, nullable=False))
    reasoning: str = Field(default="", sa_column=Column(Text, nullable=False))
    decision: str = Field(sa_column=Column(String, nullable=False))
    approved_amount: float = Field(sa_column=Column(Float, nullable=False))
    rejection_reasons: str = Field(sa_column=Column(Text, nullable=False))
    deductions: str = Field(sa_column=Column(Text, nullable=False))
    confidence_score: float = Field(sa_column=Column(Float, nullable=False))
    fraud_flags: str = Field(sa_column=Column(Text, nullable=False))
    policy_sections_referenced: str = Field(sa_column=Column(Text, nullable=False))
    notes: str = Field(sa_column=Column(Text, nullable=False))
    next_steps: str = Field(sa_column=Column(Text, nullable=False))
    created_at: str = Field(sa_column=Column(String, nullable=False))


class ClaimAppeal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, sa_column=Column(Integer, primary_key=True, autoincrement=True))
    claim_id: str = Field(sa_column=Column(String, nullable=False))
    appeal_reason: str = Field(sa_column=Column(Text, nullable=False))
    additional_notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    status: str = Field(default="PENDING", sa_column=Column(String, default="PENDING"))
    reviewer_notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: str = Field(sa_column=Column(String, nullable=False))
    resolved_at: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))


class PolicyConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, sa_column=Column(Integer, primary_key=True, autoincrement=True))
    section: str = Field(sa_column=Column(String, nullable=False, index=True))
    config_json: str = Field(sa_column=Column(Text, nullable=False))
    updated_at: str = Field(sa_column=Column(String, nullable=False))
    updated_by: str = Field(sa_column=Column(String, nullable=False))


class EvaluationLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, sa_column=Column(Integer, primary_key=True, autoincrement=True))
    claim_id: str = Field(sa_column=Column(String, nullable=False))
    ai_decision: str = Field(sa_column=Column(String, nullable=False))
    ground_truth_decision: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    is_correct: Optional[bool] = Field(default=None, sa_column=Column(Boolean, nullable=True))
    error_type: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    amount_deviation: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    created_at: str = Field(sa_column=Column(String, nullable=False))
