# OPD Claim Adjudication Tool — Implementation Plan

## Overview

An AI-powered full-stack web application that automates the adjudication (approval/rejection) of OPD insurance claims. Users submit medical documents (bills, prescriptions, reports), the system extracts structured data using GPT-4o Vision, retrieves relevant policy context via RAG, and makes an intelligent approve/reject/partial/manual-review decision using an LLM agent whose system prompt encodes all adjudication rules.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Next.js Frontend                   │
│   Submit Claim → Claim Status → Claims Dashboard     │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP (REST)
                        ▼
┌─────────────────────────────────────────────────────┐
│                  FastAPI Backend                     │
│                                                     │
│  ┌──────────────┐   ┌──────────────┐               │
│  │  Extractor   │   │ Adjudicator  │               │
│  │  Agent       │   │ Agent        │               │
│  │  GPT-4o      │   │ GPT-4o +     │               │
│  │  Vision      │   │ RAG context  │               │
│  └──────┬───────┘   └──────┬───────┘               │
│         │                  │                        │
│         ▼                  ▼                        │
│  ┌──────────────────────────────────┐               │
│  │        ChromaDB (RAG)            │               │
│  │   policy_terms.json embedded     │               │
│  └──────────────────────────────────┘               │
│                                                     │
│  ┌──────────────────────────────────┐               │
│  │        SQLite / Supabase         │               │
│  │   claims, documents, decisions   │               │
│  └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
plum-claims/
│
├── backend/
│   ├── main.py                        # FastAPI app entry point, CORS, routers
│   ├── config.py                      # Settings (API keys, DB URL, model names)
│   ├── models.py                      # All Pydantic models (request/response/DB)
│   ├── database.py                    # SQLModel engine, session, table creation
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── extractor.py               # GPT-4o Vision → DocumentExtraction
│   │   └── adjudicator.py             # RAG + system prompt → AdjudicationDecision
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── ingest.py                  # Chunk + embed policy_terms.json at startup
│   │   └── retriever.py               # Query ChromaDB, return top-k policy chunks
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── claims.py                  # POST /claims, GET /claims, GET /claims/{id}
│   │   └── health.py                  # GET /health
│   │
│   ├── prompts/
│   │   └── adjudicator_system.txt     # Full adjudication rules as system prompt
│   │
│   ├── uploads/                       # Temp storage for uploaded documents
│   ├── chroma_db/                     # ChromaDB persistent storage
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                 # Root layout
│   │   ├── page.tsx                   # Submit claim page
│   │   ├── claims/
│   │   │   └── [id]/
│   │   │       └── page.tsx           # Claim decision view
│   │   └── dashboard/
│   │       └── page.tsx               # All claims list with filters
│   │
│   ├── components/
│   │   ├── ClaimForm.tsx              # Multi-step claim submission form
│   │   ├── DocumentUpload.tsx         # Drag-and-drop file upload
│   │   ├── DecisionCard.tsx           # Shows decision badge, amount, reasons
│   │   ├── ClaimsTable.tsx            # Dashboard table with status filters
│   │   └── ConfidenceBar.tsx          # Visual confidence score indicator
│   │
│   ├── lib/
│   │   └── api.ts                     # Typed fetch wrappers for backend calls
│   │
│   ├── types/
│   │   └── index.ts                   # TypeScript types mirroring Pydantic models
│   │
│   ├── package.json
│   ├── tailwind.config.ts
│   └── .env.local
│
├── policy_terms.json                  # Source policy document (used for RAG)
├── adjudication_rules.md              # Source rules document (used for system prompt)
├── test_cases.json                    # 10 test cases for validation
├── plan.md                            # This file
└── README.md
```

---

## Pydantic Models (`backend/models.py`)

### Request Models

```python
class ClaimSubmission(BaseModel):
    member_id: str
    member_name: str
    member_join_date: date
    treatment_date: date
    claim_amount: float
    hospital_name: str | None = None
    cashless_request: bool = False
    ytd_claimed_amount: float = 0.0         # claims already made this year
    previous_claims_same_day: int = 0       # for fraud detection
```

### Extraction Models (GPT-4o Vision output)

```python
class ExtractedDocument(BaseModel):
    doc_type: Literal["prescription", "bill", "diagnostic_report", "pharmacy_bill"]
    doctor_name: str | None
    doctor_reg: str | None                  # format: STATE/NUMBER/YEAR
    patient_name: str | None
    diagnosis: str | None
    medicines: list[str]
    tests_prescribed: list[str]
    procedures: list[str]
    treatment_date: date | None
    consultation_fee: float | None
    total_amount: float | None
    line_items: list[dict]                  # itemized breakdown
    extraction_confidence: float            # 0.0 - 1.0

class ExtractionResult(BaseModel):
    documents: list[ExtractedDocument]
    merged_diagnosis: str
    merged_total: float
    date_consistent: bool
    patient_name_consistent: bool
    all_required_docs_present: bool
    missing_docs: list[str]
```

### Decision Models (Adjudication Agent output)

```python
class AdjudicationDecision(BaseModel):
    claim_id: str
    decision: Literal["APPROVED", "REJECTED", "PARTIAL", "MANUAL_REVIEW"]
    approved_amount: float
    rejection_reasons: list[str]            # rejection code strings e.g. PER_CLAIM_EXCEEDED
    deductions: dict[str, float]            # e.g. {"copay": 150, "cosmetic": 4000}
    confidence_score: float                 # 0.0 - 1.0
    fraud_flags: list[str]
    policy_sections_referenced: list[str]   # which RAG chunks were used
    notes: str
    next_steps: str
```

### Database Models (SQLModel)

```python
class Claim(SQLModel, table=True):
    id: str = Field(default_factory=..., primary_key=True)   # CLM_XXXXX
    member_id: str
    member_name: str
    member_join_date: date
    treatment_date: date
    claim_amount: float
    hospital_name: str | None
    cashless_request: bool
    ytd_claimed_amount: float
    status: str                             # PENDING, PROCESSED, ERROR
    created_at: datetime

class ClaimDocument(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    claim_id: str = Field(foreign_key="claim.id")
    doc_type: str
    file_path: str
    extracted_data: str                     # JSON string of ExtractedDocument
    created_at: datetime

class ClaimDecision(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    claim_id: str = Field(foreign_key="claim.id")
    decision: str
    approved_amount: float
    rejection_reasons: str                  # JSON array string
    deductions: str                         # JSON object string
    confidence_score: float
    fraud_flags: str                        # JSON array string
    policy_sections_referenced: str        # JSON array string
    notes: str
    next_steps: str
    created_at: datetime
```

---

## API Endpoints (`backend/routers/`)

### Claims Router

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/claims` | Submit new claim (multipart: files + JSON body) |
| `GET` | `/claims` | List all claims (with optional status filter) |
| `GET` | `/claims/{claim_id}` | Get full claim detail + decision |
| `GET` | `/claims/{claim_id}/decision` | Get decision only |
| `GET` | `/health` | Health check |

### POST /claims Request

```
Content-Type: multipart/form-data

files: [file1.jpg, file2.pdf, ...]       # medical documents
data:  ClaimSubmission (JSON string)
```

### POST /claims Response

```json
{
  "claim_id": "CLM_00001",
  "status": "PROCESSED",
  "decision": {
    "decision": "APPROVED",
    "approved_amount": 1350.0,
    "rejection_reasons": [],
    "deductions": {"copay": 150},
    "confidence_score": 0.95,
    "fraud_flags": [],
    "notes": "Claim approved. 10% co-pay applied on consultation fee.",
    "next_steps": "Reimbursement will be credited within 5-7 working days."
  },
  "extracted_data": {
    "merged_diagnosis": "Viral fever",
    "merged_total": 1500.0,
    "all_required_docs_present": true,
    "missing_docs": []
  }
}
```

---

## Agent 1: Document Extractor (`backend/agents/extractor.py`)

**Model:** `gpt-4o` with vision  
**Input:** List of uploaded file paths (images or PDFs)  
**Output:** `ExtractionResult` (Pydantic, via OpenAI structured outputs)

**How it works:**
1. Each file is base64-encoded and passed to GPT-4o as an image message
2. Prompt instructs it to extract all relevant medical fields
3. `client.beta.chat.completions.parse()` with `response_format=ExtractedDocument`
4. After all docs extracted, a merge step consolidates into `ExtractionResult`
5. Checks date consistency, patient name consistency, required docs presence

**Key prompt instruction:**
```
Extract all visible medical information from this document.
If a field is not visible or not applicable, return null.
Do not infer or guess values not present in the document.
Return extraction_confidence based on document legibility and completeness.
```

---

## Agent 2: Adjudicator (`backend/agents/adjudicator.py`)

**Model:** `gpt-4o`  
**Input:** `ExtractionResult` + `ClaimSubmission` + RAG-retrieved policy context  
**Output:** `AdjudicationDecision` (Pydantic, via OpenAI structured outputs)  
**System prompt:** Full content of `adjudication_rules.md`

**How it works:**
1. Build RAG query from diagnosis + treatment type + doc types present
2. Retrieve top-5 relevant chunks from ChromaDB (policy_terms.json)
3. Construct user message:
   ```
   POLICY CONTEXT (retrieved):
   {rag_chunks}

   CLAIM DATA:
   Member: {name}, joined {join_date}
   Treatment date: {treatment_date}
   Claim amount: ₹{amount}
   YTD claimed: ₹{ytd}
   Hospital: {hospital}
   Previous claims today: {count}

   EXTRACTED FROM DOCUMENTS:
   {extraction_result_json}

   Apply the adjudication rules from your system prompt.
   Reference which policy sections informed your decision.
   ```
4. Parse response into `AdjudicationDecision` via structured output

**Confidence score logic in prompt:**
- Hard rule fired (limit exceeded, exclusion match) → 0.95–1.0
- Soft judgement (medical necessity, partial coverage) → 0.75–0.92
- Fraud indicators present → score drops to <0.70, triggers MANUAL_REVIEW
- Extraction confidence <0.6 → force MANUAL_REVIEW

---

## RAG Setup (`backend/rag/`)

**Vector store:** ChromaDB (local persistent)  
**Embeddings:** `text-embedding-3-small` (OpenAI)  
**Source document:** `policy_terms.json`

### Chunking Strategy (`ingest.py`)

`policy_terms.json` is not plain text — it is chunked by logical sections:

| Chunk | Content |
|-------|---------|
| `coverage_consultation` | Consultation fees, sub-limit, copay %, network discount |
| `coverage_diagnostic` | Covered tests, sub-limit, pre-auth requirements |
| `coverage_pharmacy` | Sub-limit, generic drug rules, branded copay |
| `coverage_dental` | Procedures covered, sub-limit, cosmetic exclusion |
| `coverage_vision` | Eye test, glasses, LASIK exclusion |
| `coverage_alternative` | Covered treatments (Ayurveda, Homeopathy), session limit |
| `limits` | Annual limit, per-claim limit, family floater |
| `waiting_periods` | Initial, pre-existing diseases, maternity, specific ailments |
| `exclusions` | Full exclusions list |
| `network_hospitals` | List of network providers, cashless rules |
| `claim_requirements` | Required documents, submission timeline, minimum amount |

Each chunk is stored with metadata: `{"section": "...", "source": "policy_terms.json"}`

### Retrieval (`retriever.py`)

```python
def retrieve_policy_context(query: str, top_k: int = 5) -> list[str]:
    # embed query → similarity search → return top_k chunk texts
```

Query is built from: `"{diagnosis} {doc_types} {procedures} {medicines}"`

---

## System Prompt (`backend/prompts/adjudicator_system.txt`)

The system prompt contains the **complete adjudication_rules.md** verbatim, followed by:

```
You are an OPD insurance claim adjudication agent for Plum Insurance.
Your role is to evaluate claims strictly according to the rules above.

Rules for your response:
1. Follow the 5-step adjudication flow exactly.
2. Use rejection codes exactly as specified (e.g. PER_CLAIM_EXCEEDED).
3. Calculate co-pay and deductions numerically.
4. Assign confidence_score based on certainty of your decision.
5. If confidence < 0.70 or fraud flags are detected, set decision = MANUAL_REVIEW.
6. For partial approvals, approved_amount must reflect only the covered portion.
7. policy_sections_referenced must list which policy clauses you applied.
8. next_steps must be actionable and specific to the decision.
9. Never approve excluded treatments. Never exceed hard limits.
10. When in doubt, refer for MANUAL_REVIEW rather than approving.
```

---

## Frontend Pages (`frontend/`)

### Page 1: Submit Claim (`app/page.tsx`)

**Components:**
- `ClaimForm` — two sections:
  - Member details: member ID, name, join date
  - Claim details: treatment date, amount, hospital (optional), cashless toggle
- `DocumentUpload` — drag-and-drop, accepts JPG/PNG/PDF, shows thumbnails
- Submit button → calls `POST /claims` → redirects to `/claims/{id}`

### Page 2: Claim Decision (`app/claims/[id]/page.tsx`)

**Components:**
- `DecisionCard` — large status badge (green/red/yellow/orange), approved amount
- Rejection reasons list (if any)
- Deductions breakdown table
- `ConfidenceBar` — visual bar showing confidence score
- Extracted data summary (diagnosis, doctor, documents found)
- Next steps section

### Page 3: Dashboard (`app/dashboard/page.tsx`)

**Components:**
- `ClaimsTable` — columns: Claim ID, Member, Date, Amount, Decision, Confidence, Actions
- Filter bar: filter by decision status
- Each row links to `/claims/{id}`

---

## Data Flow (End to End)

```
1. User fills ClaimForm + uploads 1-3 documents
2. Frontend sends POST /claims (multipart)
3. FastAPI:
   a. Validates ClaimSubmission via Pydantic
   b. Saves files to /uploads/{claim_id}/
   c. Creates Claim record in DB (status=PENDING)
   d. Calls extractor.py:
      - GPT-4o Vision on each file → ExtractedDocument
      - Merge all → ExtractionResult
      - Save each doc + extracted JSON to ClaimDocument table
   e. Calls adjudicator.py:
      - Build RAG query from diagnosis
      - Retrieve policy context from ChromaDB
      - Call GPT-4o with system prompt + context + extracted data
      - Parse → AdjudicationDecision
      - Save to ClaimDecision table
   f. Update Claim status=PROCESSED
   g. Return full response
4. Frontend receives response → redirects to /claims/{id}
5. Decision page renders full result
```

---

## OpenAI Structured Output Pattern

Used in both agents. Example for adjudicator:

```python
from openai import OpenAI
from models import AdjudicationDecision

client = OpenAI(api_key=settings.OPENAI_API_KEY)

response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ],
    response_format=AdjudicationDecision
)

decision: AdjudicationDecision = response.choices[0].message.parsed
```

---

## Environment Variables

### Backend (`.env`)
```
OPENAI_API_KEY=sk-...
DATABASE_URL=sqlite:///./claims.db
CHROMA_PERSIST_DIR=./chroma_db
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=10
ALLOWED_ORIGINS=http://localhost:3000
```

### Frontend (`.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Build Order

1. `backend/config.py` — settings
2. `backend/models.py` — all Pydantic + SQLModel models
3. `backend/database.py` — DB engine + table creation
4. `backend/rag/ingest.py` — chunk and embed policy_terms.json
5. `backend/rag/retriever.py` — ChromaDB query wrapper
6. `backend/prompts/adjudicator_system.txt` — full system prompt
7. `backend/agents/extractor.py` — GPT-4o Vision extraction
8. `backend/agents/adjudicator.py` — RAG + LLM adjudication
9. `backend/routers/claims.py` — API endpoints wiring everything
10. `backend/main.py` — FastAPI app, startup RAG ingestion
11. `frontend/` — Next.js pages and components
12. Test all 10 test cases from `test_cases.json`

---

## Test Cases Coverage

| TC | Scenario | Expected Decision |
|----|----------|------------------|
| TC001 | Normal fever, valid docs | APPROVED (₹1350, 10% copay) |
| TC002 | Root canal + cosmetic whitening | PARTIAL (₹8000, whitening rejected) |
| TC003 | Claim ₹7500 > per-claim limit ₹5000 | REJECTED (PER_CLAIM_EXCEEDED) |
| TC004 | No prescription submitted | REJECTED (MISSING_DOCUMENTS) |
| TC005 | Diabetes within 90-day waiting period | REJECTED (WAITING_PERIOD) |
| TC006 | Ayurvedic treatment within limits | APPROVED (₹4000) |
| TC007 | MRI without pre-authorization | REJECTED (PRE_AUTH_MISSING) |
| TC008 | 3 claims same day, fraud pattern | MANUAL_REVIEW |
| TC009 | Weight loss treatment (excluded) | REJECTED (SERVICE_NOT_COVERED) |
| TC010 | Network hospital, cashless | APPROVED (₹3600, network discount) |

---

## Deployment

| Service | Platform | Notes |
|---------|----------|-------|
| Frontend | Vercel | `frontend/` directory, env var: NEXT_PUBLIC_API_URL |
| Backend | Railway / Render | `backend/` directory, all env vars set in dashboard |
| Database | Supabase (prod) | Switch DATABASE_URL from SQLite to PostgreSQL |
| ChromaDB | Hosted on same backend server | persisted to disk |

---

## Bonus Features (all required)

### 1. Confidence Score Visualisation

Already baked into `DecisionCard` and `ConfidenceBar` component on the claim decision page.

- Visual progress bar with colour: green (>0.85), amber (0.70–0.85), red (<0.70)
- Tooltip explaining what the score means
- Score breakdown shown: extraction confidence + rule certainty + fraud signal weight
- Stored in `ClaimDecision.confidence_score`, always returned in API response

---

### 2. Appeals / Manual Review Workflow

**New DB table:**

```python
class ClaimAppeal(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    claim_id: str = Field(foreign_key="claim.id")
    appeal_reason: str
    additional_notes: str | None
    status: str          # PENDING, UNDER_REVIEW, UPHELD, DISMISSED
    reviewer_notes: str | None
    created_at: datetime
    resolved_at: datetime | None
```

**New Pydantic models:**

```python
class AppealSubmission(BaseModel):
    claim_id: str
    appeal_reason: str
    additional_notes: str | None = None

class AppealResolution(BaseModel):
    appeal_id: int
    new_decision: Literal["APPROVED", "REJECTED", "PARTIAL"]
    approved_amount: float
    reviewer_notes: str
```

**New API endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/claims/{id}/appeal` | Submit an appeal for a rejected/partial claim |
| `GET` | `/appeals` | List all pending appeals (admin) |
| `GET` | `/appeals/{appeal_id}` | Get single appeal detail |
| `PATCH` | `/appeals/{appeal_id}/resolve` | Admin resolves appeal with new decision |

**Appeal flow:**
1. Member sees rejection on decision page → clicks "Appeal this Decision"
2. Fills appeal form: reason dropdown + free text notes
3. `POST /claims/{id}/appeal` creates `ClaimAppeal` with status=PENDING
4. Claim status updated to `UNDER_REVIEW`
5. Admin sees it in manual review queue (dashboard)
6. Admin reviews original docs + extracted data + AI decision reasoning
7. Admin submits resolution via `PATCH /appeals/{id}/resolve`
8. `ClaimDecision` updated with new decision, `ClaimAppeal` status set to UPHELD/DISMISSED

**Frontend pages:**
- Appeal form modal on `/claims/{id}` (shown only for REJECTED/PARTIAL decisions)
- `/admin/appeals` — queue of all pending appeals with full claim context

---

### 3. Admin Dashboard for Policy Configuration

**What it does:** Lets admin view and edit the active policy terms without touching code. Changes are persisted to DB and the RAG index is re-built automatically.

**New DB table:**

```python
class PolicyConfig(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    section: str                        # e.g. "consultation_fees", "pharmacy"
    config_json: str                    # JSON string of the section
    updated_at: datetime
    updated_by: str
```

**New API endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/policy` | Get full active policy config |
| `PATCH` | `/admin/policy/{section}` | Update a specific policy section |
| `POST` | `/admin/policy/rebuild-rag` | Re-embed updated policy into ChromaDB |

**Frontend page: `/admin/policy`**

Organised into tabs per section:
- **Limits** — edit annual limit, per-claim limit, family floater (number inputs)
- **Sub-limits** — edit per-category limits (consultation, pharmacy, dental, etc.)
- **Waiting Periods** — edit days for initial, pre-existing, maternity, specific ailments
- **Exclusions** — add/remove items from exclusions list
- **Network Hospitals** — add/remove hospitals from network list
- **Covered Services** — toggle covered tests, procedures, alternative treatments

Each section has a Save button → `PATCH /admin/policy/{section}` → triggers RAG rebuild.
Warning banner shown if RAG is out of sync with latest policy.

---

### 4. Evaluation Metrics for AI Accuracy

**Purpose:** Track how well the AI decisions align with expected outcomes, monitor accuracy over time, and surface systematic errors.

**New DB table:**

```python
class EvaluationLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    claim_id: str = Field(foreign_key="claim.id")
    ai_decision: str
    ground_truth_decision: str | None       # set after human review or appeal resolution
    is_correct: bool | None
    error_type: str | None                  # FALSE_POSITIVE, FALSE_NEGATIVE, AMOUNT_ERROR
    amount_deviation: float | None          # |ai_amount - actual_amount|
    created_at: datetime
```

**New API endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/metrics` | Aggregate accuracy metrics |
| `POST` | `/admin/metrics/run-test-suite` | Run all 10 test cases, compare to expected |
| `PATCH` | `/admin/metrics/{claim_id}/label` | Admin labels ground truth for a decision |

**Metrics computed (`GET /admin/metrics`):**

```json
{
  "total_claims": 150,
  "decisions_breakdown": {
    "APPROVED": 80, "REJECTED": 45, "PARTIAL": 18, "MANUAL_REVIEW": 7
  },
  "accuracy": {
    "overall": 0.91,
    "precision": 0.93,
    "recall": 0.88,
    "false_positive_rate": 0.07,
    "false_negative_rate": 0.12
  },
  "amount_accuracy": {
    "mean_absolute_deviation": 234.5,
    "within_10_percent": 0.87
  },
  "confidence_calibration": {
    "high_confidence_correct_rate": 0.96,
    "low_confidence_correct_rate": 0.71
  },
  "test_suite_results": {
    "passed": 9,
    "failed": 1,
    "last_run": "2024-11-03T10:30:00"
  }
}
```

**Frontend page: `/admin/metrics`**

- Summary cards: accuracy %, total claims, approval rate
- Bar chart: decisions breakdown
- Line chart: accuracy trend over time (last 30 days)
- Test suite runner button → shows pass/fail per test case with diff view
- Table of recent decisions with ground truth labels editable inline

---

### 5. CI/CD Pipeline (GitHub Actions)

**File: `.github/workflows/ci.yml`**

Runs on every push to `main` and every PR:

```
Jobs:
  backend-test:
    - Install Python deps
    - Run pytest (unit tests for rule logic, RAG retrieval)
    - Run test suite against mock OpenAI responses

  frontend-lint:
    - npm install
    - eslint + tsc --noEmit (TypeScript check)

  integration-test:
    - Spin up FastAPI + SQLite
    - Run all 10 test cases via API
    - Assert decisions match expected outputs

  deploy (on main merge only):
    - Deploy backend to Railway
    - Deploy frontend to Vercel
```

---

## Updated Frontend Pages (Full List)

| Route | Page | Description |
|-------|------|-------------|
| `/` | Submit Claim | Claim form + document upload |
| `/claims/[id]` | Claim Decision | Full decision view, appeal button |
| `/dashboard` | My Claims | Member's claim history table |
| `/claims/[id]/appeal` | Appeal Form | Appeal submission for rejected claims |
| `/admin` | Admin Home | Links to all admin sections |
| `/admin/appeals` | Appeals Queue | All pending appeals for manual review |
| `/admin/policy` | Policy Config | Edit policy terms, trigger RAG rebuild |
| `/admin/metrics` | Evaluation Metrics | AI accuracy dashboard + test suite runner |

---

## Updated Build Order

1. `backend/config.py`
2. `backend/models.py` — include Appeal, PolicyConfig, EvaluationLog models
3. `backend/database.py`
4. `backend/rag/ingest.py`
5. `backend/rag/retriever.py`
6. `backend/prompts/adjudicator_system.txt`
7. `backend/agents/extractor.py`
8. `backend/agents/adjudicator.py`
9. `backend/routers/claims.py`
10. `backend/routers/appeals.py`
11. `backend/routers/admin.py` — policy config + RAG rebuild + metrics
12. `backend/main.py`
13. `frontend/` — all 8 pages + components
14. `.github/workflows/ci.yml`
15. End-to-end test: all 10 test cases + appeal flow + admin policy edit
