# Plum OPD Claim Adjudication Tool

An AI-powered full-stack web application that automates the adjudication (approval / rejection / partial / manual-review) of Outpatient Department (OPD) insurance claims. Users submit medical documents (bills, prescriptions, diagnostic reports), the system extracts structured data using GPT-4o Vision, retrieves relevant policy context via RAG, and makes an intelligent decision using an LLM agent whose system prompt encodes all adjudication rules.

**10 / 10 test cases passing. All 5 bonus features implemented.**

---

## Table of Contents

1. [Architecture](#architecture)
2. [Tech Stack](#tech-stack)
3. [Local Setup](#local-setup)
4. [Environment Variables](#environment-variables)
5. [API Documentation](#api-documentation)
6. [Decision Logic Flowchart](#decision-logic-flowchart)
7. [Assumptions Made](#assumptions-made)
8. [Test Cases](#test-cases)
9. [Bonus Features](#bonus-features)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js 14 Frontend                      │
│                                                             │
│  / (home)   /claims/new   /claims/[id]   /dashboard         │
│  /admin     /admin/appeals  /admin/policy  /admin/metrics   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP REST (multipart / JSON)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                         │
│                                                             │
│  ┌─────────────────────┐    ┌──────────────────────────┐   │
│  │   Extractor Agent   │    │   Adjudicator Agent      │   │
│  │   GPT-4o Vision     │    │   GPT-4o + RAG context   │   │
│  │   Structured Output │    │   Structured Output      │   │
│  └──────────┬──────────┘    └─────────────┬────────────┘   │
│             │                             │                  │
│             ▼                             ▼                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              ChromaDB  (RAG vector store)             │   │
│  │     policy_terms.json  →  11 embedded chunks         │   │
│  │     text-embedding-3-small  (OpenAI)                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   SQLite Database                     │   │
│  │  Claim · ClaimDocument · ClaimDecision               │   │
│  │  ClaimAppeal · PolicyConfig · EvaluationLog          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow (end to end)

```
1. User fills claim form + uploads 1-3 medical documents
2. Frontend  →  POST /claims  (multipart: files + JSON)
3. FastAPI validates ClaimSubmission (Pydantic)
4. Files saved to  /uploads/{claim_id}/
5. Claim record created in DB  (status = PENDING)
6. Extractor Agent:
     ├─ Each file  →  base64  →  GPT-4o Vision
     └─ Returns ExtractedDocument per file  →  merged into ExtractionResult
7. Adjudicator Agent:
     ├─ RAG query built from diagnosis + doc types
     ├─ Top-5 policy chunks retrieved from ChromaDB
     ├─ GPT-4o called with: system prompt (adjudication rules)
     │                       + policy context (RAG)
     │                       + claim submission data
     │                       + extraction result
     └─ Returns AdjudicationDecision (structured output)
8. Decision + EvaluationLog saved to DB
9. Claim status  →  PROCESSED
10. Full response returned to frontend
11. Frontend redirects to  /claims/{id}  →  decision rendered
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | Python 3.12, FastAPI, Uvicorn |
| AI / LLM | OpenAI GPT-4o (Vision + structured outputs) |
| Embeddings | OpenAI text-embedding-3-small |
| Vector Store | ChromaDB (local persistent) |
| Database | SQLite via SQLModel (dev) / PostgreSQL via Supabase (prod) |
| Document Processing | GPT-4o Vision (images), PyMuPDF (PDF → PNG render) |
| CI / CD | GitHub Actions |

---

## Local Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- An OpenAI API key

### 1. Clone the repository

```bash
git clone https://github.com/sjgod1427/Plum.git
cd Plum
```

### 2. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Copy env file and add your OpenAI key
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

# Start the server
uvicorn main:app --reload --port 8000
```

The backend starts at `http://localhost:8000`.  
On first startup it automatically:
- Creates all database tables
- Chunks and embeds `policy_terms.json` into ChromaDB (11 policy sections)

Interactive API docs: `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Create env file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start dev server
npm run dev
```

The frontend starts at `http://localhost:3000`.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `DATABASE_URL` | No | `sqlite:///./claims.db` | SQLAlchemy DB URL |
| `CHROMA_PERSIST_DIR` | No | `./chroma_db` | ChromaDB storage path |
| `UPLOAD_DIR` | No | `./uploads` | Uploaded document storage |
| `MAX_FILE_SIZE_MB` | No | `10` | Max upload size per file |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | CORS origins (comma-separated) |
| `POLICY_TERMS_PATH` | No | `../policy_terms.json` | Path to policy source file |

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000` | Backend base URL |

---

## API Documentation

Full interactive docs available at `/docs` (Swagger UI) when the backend is running.

### Claims

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/claims` | Submit a new claim (multipart: `files[]` + `data` JSON string) |
| `POST` | `/claims/direct` | Submit claim with pre-built extraction (used by test suite) |
| `GET` | `/claims` | List all claims (optional `?status=PROCESSED`) |
| `GET` | `/claims/{id}` | Get full claim detail with decision and documents |
| `GET` | `/claims/{id}/decision` | Get decision only |

#### POST /claims — Request

```
Content-Type: multipart/form-data

files:  [prescription.jpg, bill.pdf, ...]   (JPG / PNG / PDF, max 10 MB each)
data:   {
  "member_id": "EMP001",
  "member_name": "Rajesh Kumar",
  "member_join_date": "2024-01-01",
  "treatment_date": "2024-11-01",
  "claim_amount": 1500.0,
  "hospital_name": "Apollo Hospitals",   // optional
  "cashless_request": false,
  "ytd_claimed_amount": 0.0,
  "previous_claims_same_day": 0
}
```

#### POST /claims — Response

```json
{
  "claim_id": "CLM_094AFF0A",
  "status": "PROCESSED",
  "decision": {
    "decision": "APPROVED",
    "approved_amount": 1350.0,
    "rejection_reasons": [],
    "deductions": [{ "reason": "10% co-pay on consultation fee", "amount": 150.0 }],
    "confidence_score": 0.95,
    "fraud_flags": [],
    "policy_sections_referenced": ["coverage_consultation", "limits"],
    "notes": "Claim approved. 10% co-pay applied on consultation fee.",
    "next_steps": "Reimbursement will be credited within 5-7 working days.",
    "reasoning": "Step 0 (FRAUD): no flags. Step 1 (ELIGIBILITY): ..."
  },
  "extracted_data": {
    "merged_diagnosis": "Viral fever",
    "merged_total": 1500.0,
    "all_required_docs_present": true,
    "missing_docs": []
  }
}
```

### Appeals

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/claims/{id}/appeal` | Submit appeal for a rejected or partial claim |
| `GET` | `/appeals` | List all appeals (optional `?status=PENDING`) |
| `GET` | `/appeals/{appeal_id}` | Get single appeal with full claim context |
| `PATCH` | `/appeals/{appeal_id}/resolve` | Admin resolves appeal with new decision |

### Admin — Policy

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/admin/policy` | Get active policy configuration |
| `PATCH` | `/admin/policy/{section}` | Update a policy section and re-embed into ChromaDB |
| `POST` | `/admin/policy/rebuild-rag` | Rebuild full RAG index from current policy |

Valid `{section}` values: `limits`, `coverage_consultation`, `coverage_diagnostic`, `coverage_pharmacy`, `coverage_dental`, `coverage_vision`, `coverage_alternative`, `waiting_periods`, `exclusions`, `network_hospitals`, `claim_requirements`

### Admin — Metrics

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/admin/metrics` | AI accuracy metrics + per-case breakdown |
| `POST` | `/admin/metrics/run-test-suite` | Run all 10 test cases, compare AI vs ground truth |
| `PATCH` | `/admin/metrics/{claim_id}/label` | Label a claim with its ground truth decision |

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check → `{"status": "ok"}` |

---

## Decision Logic Flowchart

```
                    ┌─────────────────────┐
                    │   Claim Submitted    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Step 0: FRAUD CHECK │
                    │  previous_claims     │
                    │  same day >= 3?      │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                  YES                    NO
                    │                    │
                    ▼                    ▼
           ┌────────────────┐  ┌─────────────────────┐
           │ MANUAL_REVIEW  │  │ Step 1: ELIGIBILITY  │
           └────────────────┘  │ Policy active?       │
                               │ Waiting periods met? │
                               └──────────┬───────────┘
                                          │
                               ┌──────────┴──────────┐
                             FAIL                   PASS
                               │                    │
                               ▼                    ▼
                        ┌────────────┐  ┌──────────────────────┐
                        │  REJECTED  │  │ Step 2: DOCUMENTS     │
                        │ WAITING_   │  │ Prescription present? │
                        │ PERIOD /   │  │ Legible & dated?      │
                        │ POLICY_    │  │ Doctor reg valid?     │
                        │ INACTIVE   │  └──────────┬────────────┘
                        └────────────┘             │
                                        ┌──────────┴──────────┐
                                      FAIL                   PASS
                                        │                    │
                                        ▼                    ▼
                                 ┌────────────┐  ┌──────────────────────┐
                                 │  REJECTED  │  │ Step 3: COVERAGE      │
                                 │ MISSING_   │  │ Treatment covered?    │
                                 │ DOCUMENTS  │  │ Not in exclusions?   │
                                 └────────────┘  │ Pre-auth obtained?   │
                                                 └──────────┬────────────┘
                                                            │
                                                 ┌──────────┴──────────┐
                                               FAIL                   PASS
                                                 │                    │
                                                 ▼                    ▼
                                          ┌────────────┐  ┌──────────────────────┐
                                          │  REJECTED  │  │ Step 4: LIMITS        │
                                          │ SERVICE_   │  │ Annual limit OK?     │
                                          │ NOT_COVERED│  │ Per-claim limit OK?  │
                                          │ EXCLUDED_  │  │ Sub-limit OK?        │
                                          │ CONDITION  │  └──────────┬────────────┘
                                          └────────────┘             │
                                                          ┌──────────┴──────────┐
                                                        FAIL                   PASS
                                                          │                    │
                                                          ▼                    ▼
                                                   ┌────────────┐  ┌──────────────────────┐
                                                   │  REJECTED  │  │ Step 5: MEDICAL       │
                                                   │ PER_CLAIM_ │  │ NECESSITY             │
                                                   │ EXCEEDED / │  │ Diagnosis justifies  │
                                                   │ SUB_LIMIT_ │  │ treatment?           │
                                                   │ EXCEEDED   │  └──────────┬────────────┘
                                                   └────────────┘             │
                                                               ┌──────────────┴──────────────┐
                                                           ALL OK                        PARTIAL / DOUBT
                                                               │                              │
                                                               ▼                              ▼
                                                  ┌─────────────────────┐      ┌─────────────────────┐
                                                  │  Apply co-pay &     │      │  PARTIAL approval   │
                                                  │  deductions         │      │  or MANUAL_REVIEW   │
                                                  │  Network discount   │      │  if conf < 0.70     │
                                                  └──────────┬──────────┘      └─────────────────────┘
                                                             │
                                                             ▼
                                                  ┌─────────────────────┐
                                                  │      APPROVED        │
                                                  └─────────────────────┘
```

### Decision Output Codes

| Code | Category | Meaning |
|---|---|---|
| `WAITING_PERIOD` | Eligibility | Treatment during waiting period |
| `POLICY_INACTIVE` | Eligibility | Policy not active on treatment date |
| `MEMBER_NOT_COVERED` | Eligibility | Member not in policy |
| `MISSING_DOCUMENTS` | Documents | Required docs not submitted |
| `INVALID_PRESCRIPTION` | Documents | Prescription invalid or missing |
| `DOCTOR_REG_INVALID` | Documents | Doctor registration number invalid |
| `DATE_MISMATCH` | Documents | Document dates inconsistent |
| `SERVICE_NOT_COVERED` | Coverage | Treatment not in covered services |
| `EXCLUDED_CONDITION` | Coverage | Condition explicitly excluded |
| `PRE_AUTH_MISSING` | Coverage | Pre-authorization required but absent |
| `PER_CLAIM_EXCEEDED` | Limits | Single claim exceeds ₹5,000 limit |
| `ANNUAL_LIMIT_EXCEEDED` | Limits | Yearly limit exhausted |
| `SUB_LIMIT_EXCEEDED` | Limits | Category sub-limit exceeded |
| `NOT_MEDICALLY_NECESSARY` | Medical | Diagnosis does not justify treatment |
| `COSMETIC_PROCEDURE` | Medical | Cosmetic / aesthetic procedure |

---

## Assumptions Made

1. **Member join date defaults to 2024-01-01** when not provided in the claim form. All 10 test cases except TC005 use this default, which places treatment dates well past the 30-day initial waiting period.

2. **Per-claim limit (₹5,000) applies to general OPD only.** Dental, diagnostic, pharmacy, and alternative medicine claims use their own category sub-limits (₹10,000 dental, ₹10,000 diagnostic, ₹15,000 pharmacy, ₹8,000 alternative). This is not stated explicitly in the policy but is implied by the sub-limit structure.

3. **Waiting period violation results in full REJECTED, never PARTIAL.** Even if some line items could otherwise be covered, a waiting-period breach rejects the entire claim.

4. **Cashless network claims use 20% network discount only — no additional co-pay.** The policy lists both network discount (20%) and consultation co-pay (10%); applying both would be a double deduction. Network cashless claims apply only the network discount.

5. **Fraud check runs before all other steps.** `previous_claims_same_day >= 3` immediately routes to MANUAL_REVIEW regardless of document validity or coverage.

6. **Doctor registration format is validated structurally** (STATE/NUMBER/YEAR) but not against a real MCI database. Any string matching the format is treated as valid.

7. **MRI and CT Scan require pre-authorization for claims above ₹10,000.** The policy states these require pre-auth but does not specify a threshold; ₹10,000 is used as a reasonable threshold consistent with the test case (TC007: ₹15,000 MRI rejected).

8. **Extraction confidence below 0.6 forces MANUAL_REVIEW** regardless of the adjudication outcome. This guards against hallucinated extraction on blurry or low-quality documents.

9. **YTD claimed amount is provided by the caller** and trusted as accurate. There is no cross-claim aggregation query in this implementation (out of scope for a single-tenant demo).

10. **Vitamins and supplements are excluded unless the diagnosis specifically indicates a deficiency.** The policy lists them as excluded "unless prescribed for deficiency" — the adjudicator is instructed to treat a deficiency diagnosis as an exception.

11. **The test suite uses fixed claim IDs** (`CLM_TC001` … `CLM_TC010`) with an upsert pattern (delete-then-insert) so repeated runs never accumulate duplicate records in the database.

12. **SQLite is used for local development.** The `DATABASE_URL` environment variable can be switched to a PostgreSQL/Supabase connection string for production with no code changes (SQLModel is the ORM layer).

---

## Test Cases

All 10 provided test cases pass. Results from the live test suite run:

| ID | Scenario | Expected | Result | Amount |
|---|---|---|---|---|
| TC001 | Fever consultation, valid docs | APPROVED | APPROVED | ₹1,400 |
| TC002 | Root canal + cosmetic whitening | PARTIAL | PARTIAL | ₹8,000 |
| TC003 | Claim ₹7,500 > per-claim limit ₹5,000 | REJECTED | REJECTED | — |
| TC004 | No prescription submitted | REJECTED | REJECTED | — |
| TC005 | Diabetes within 90-day waiting period | REJECTED | REJECTED | — |
| TC006 | Ayurvedic Panchakarma therapy | APPROVED | APPROVED | ₹3,700 |
| TC007 | MRI without pre-authorization | REJECTED | REJECTED | — |
| TC008 | 3 claims same day (fraud pattern) | MANUAL_REVIEW | MANUAL_REVIEW | — |
| TC009 | Weight loss treatment (excluded) | REJECTED | REJECTED | — |
| TC010 | Apollo Hospitals cashless claim | APPROVED | APPROVED | ₹3,600 |

---

## Bonus Features

### 1. Confidence Score Visualisation
Every decision carries a `confidence_score` (0.0–1.0). Displayed as a colour-coded bar on the claim decision page and as a percentage in the dashboard table.
- Green (> 85%) — high certainty hard-rule decision
- Amber (70–85%) — soft judgement, mixed coverage
- Red (< 70%) — low certainty, auto-routes to MANUAL_REVIEW

### 2. Appeals / Manual Review Workflow
Members can appeal any REJECTED or PARTIAL decision. The appeal appears in the admin queue (`/admin/appeals`). An admin reviews the original documents, AI reasoning, and submits a resolution (UPHELD / DISMISSED) with reviewer notes. The claim decision is updated accordingly.

### 3. Admin Policy Configuration Dashboard
`/admin/policy` lets admins view and edit all policy sections (limits, sub-limits, waiting periods, exclusions, network hospitals, covered services) through a live UI. Changes are persisted to the database and the ChromaDB RAG index is automatically rebuilt so the next adjudication uses the updated policy.

### 4. Evaluation Metrics for AI Accuracy
`/admin/metrics` shows overall accuracy, precision, recall, false positive / negative rates, and mean amount deviation — all computed against the 10 known test cases. Each case displays its ground truth, AI decision, confidence score, rejection reasons, and the full chain-of-thought reasoning. The "Run Test Suite" button re-runs all 10 cases live and refreshes the metrics.

### 5. CI/CD Pipeline (GitHub Actions)
`.github/workflows/ci.yml` runs on every push and pull request:
- **backend-test**: installs Python deps, runs pytest
- **frontend-lint**: `npm install`, ESLint, `tsc --noEmit`
- **integration-test**: spins up FastAPI + SQLite, runs all 10 test cases via the API
- **deploy** (main branch only): deploys backend to Railway, frontend to Vercel

### Advanced Technique — RAG
Policy terms are chunked into 11 semantic sections and embedded using `text-embedding-3-small`. For each claim, a query is built from the diagnosis and document types, and the top-5 most relevant policy chunks are retrieved from ChromaDB and injected into the adjudicator's context window. This ensures the LLM reasons against the exact policy clauses relevant to the claim rather than relying on memorised training data.
