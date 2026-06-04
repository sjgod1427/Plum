# OPD Claim Adjudication Rules

## Overview
This document outlines the rules and logic for adjudicating (approving/rejecting) OPD insurance claims. The system should evaluate claims based on these rules in the specified order.

## Adjudication Flow

### Pre-Step: Duplicate Check
- If `is_duplicate_claim` flag is True: **REJECT immediately** with `DUPLICATE_CLAIM`. Do not evaluate further.

### Step 0: Fraud Check
- If `previous_claims_same_day >= 3`: **MANUAL_REVIEW** immediately. Do not evaluate further.
- If extraction confidence < 0.5 on any document: flag as low quality, **MANUAL_REVIEW**.

### Step 1: Basic Eligibility Check
- **Policy Status**: Policy must be active on the date of treatment
- **Dependent Age**: If claim is for a dependent and `dependent_age > 25`: **REJECT** with `DEPENDENT_AGE_EXCEEDED`
- **Waiting Period**: Check if waiting periods have been satisfied (`treatment_date − member_join_date`). Never use gestation weeks or disease onset as a proxy.
- **Member Verification**: Claimant must be a covered member (employee/dependent)

### Step 2: Document Validation
All submitted documents must meet these criteria:
- **Legibility**: Documents must be clear and readable
- **Completeness**: All required fields must be visible
- **Authenticity**: 
  - Doctor's registration number must be valid (format: [State Code]/[Number]/[Year])
  - Hospital/Clinic registration must be verifiable
  - Bills must have proper headers and stamps
- **Date Consistency**: Date gap is computed across document dates.
  - Gap = 0: OCR noise — minor confidence deduction only.
  - Gap 1–7 days (soft mismatch): Normal pharmacy pickup delay. Route to **MANUAL_REVIEW**. Never reject with `DATE_MISMATCH`.
  - Gap > 7 days (hard mismatch): **REJECT** with `DATE_MISMATCH`.
- **Patient Details**: Name and age must match policy records (minor variations acceptable)

### Step 3: Coverage Verification
Check if the treatment/service is covered:
- Compare against covered services list
- Verify it's not in exclusions list
- Check for pre-authorization requirements
- **OTC Medicines**: Paracetamol, Antacids, and generic Vitamins (unless prescribed for a diagnosed deficiency) are not covered. If a bill contains both covered prescription medicines and OTC items as separate line items, approve covered items only → PARTIAL decision.
- **Teleconsultation**: Video/phone consultations via registered platforms (Practo, Apollo 24/7, mFine, etc.) are covered under consultation fees. No co-pay on fees ≤ ₹500/visit.
- **Mental Health OPD**: Psychiatrist and psychologist consultations are covered from 2024 onwards under consultation sub-limit (₹2,500/visit).
- **Duplicate Claims**: Handled at Pre-Step before eligibility check (see above).

### Step 4: Limit Validation
Verify claim amount against applicable limits:
1. **Annual Limit**: Total claims YTD + current claim ≤ ₹25,000
2. **Sub-limits**: Category-specific limits — see coverage table below
3. **Per-claim Limit**: Single general OPD claim cannot exceed ₹5,000. Specialty categories (dental, diagnostic, physiotherapy, etc.) use their own sub-limits.
4. **Co-payment Calculation**: Apply co-pay percentages where applicable
5. **Physiotherapy Session Cap**: Maximum 8 sessions per year. If sessions_claimed > cap, approve up to cap → PARTIAL.

#### Coverage Categories & Sub-limits

| Category | Per-claim / Sub-limit | Notes |
|---|---|---|
| General OPD | ₹5,000 per claim | Consultation + pharmacy/medicines |
| Dental | ₹10,000/year | Cosmetic procedures excluded |
| Diagnostic | ₹10,000/year | MRI/CT need pre-auth above ₹10k |
| Pharmacy | ₹15,000/year | 30% co-pay on branded drugs |
| Vision | ₹5,000/year | |
| Alternative Medicine | ₹8,000/year | Ayurveda, Homeopathy, Unani |
| **Physiotherapy** | **₹10,000/year, max 8 sessions** | **Not subject to ₹5,000 per-claim limit** |
| **Teleconsultation** | **₹500 per visit** | **No co-pay; registered platforms only** |
| **Mental Health OPD** | **₹2,500 per visit** | **Covered from 2024; standard co-pay** |

### Step 5: Medical Necessity Review
Evaluate if treatment was medically necessary:
- Diagnosis must justify the treatment
- Prescription must align with diagnosis
- Test results must support the diagnosis (if applicable)
- Treatment must follow standard medical protocols

## Approval Conditions
A claim is **APPROVED** when ALL of the following are true:
- ✅ Policy is active and waiting period satisfied
- ✅ All required documents are submitted and valid
- ✅ Treatment is covered under policy
- ✅ Claim amount is within limits (after co-pay)
- ✅ Medical necessity is established
- ✅ No fraud indicators detected

## Rejection Reasons
A claim is **REJECTED** if ANY of the following apply:

### Category 1: Eligibility Issues
- `POLICY_INACTIVE`: Policy not active on treatment date
- `WAITING_PERIOD`: Treatment during waiting period
- `MEMBER_NOT_COVERED`: Claimant not found in policy records
- `DEPENDENT_AGE_EXCEEDED`: Dependent child exceeds maximum covered age of 25 years

### Category 2: Documentation Issues
- `MISSING_DOCUMENTS`: Required documents not submitted
- `ILLEGIBLE_DOCUMENTS`: Documents not readable
- `INVALID_PRESCRIPTION`: Prescription missing or invalid
- `DOCTOR_REG_INVALID`: Doctor registration number invalid/missing
- `DATE_MISMATCH`: Document dates don't match
- `PATIENT_MISMATCH`: Patient details don't match records

### Category 3: Coverage Issues
- `SERVICE_NOT_COVERED`: Treatment/service not covered
- `EXCLUDED_CONDITION`: Condition in exclusions list
- `PRE_AUTH_MISSING`: Pre-authorization required but not obtained

### Category 4: Limit Issues
- `ANNUAL_LIMIT_EXCEEDED`: Annual limit exhausted
- `SUB_LIMIT_EXCEEDED`: Category sub-limit exceeded
- `PER_CLAIM_EXCEEDED`: Single claim limit exceeded

### Category 5: Medical Issues
- `NOT_MEDICALLY_NECESSARY`: Treatment not justified by diagnosis
- `EXPERIMENTAL_TREATMENT`: Experimental/unproven treatment
- `COSMETIC_PROCEDURE`: Cosmetic/aesthetic procedure

### Category 6: Process Issues
- `LATE_SUBMISSION`: Submitted after 30-day deadline
- `DUPLICATE_CLAIM`: Same treatment already claimed
- `BELOW_MIN_AMOUNT`: Claim below ₹500 minimum

## Special Scenarios

### 1. Partial Approval
Claims can be partially approved when:
- Part of the treatment is covered, part is not
- Claim exceeds limits (approve up to limit)
- Co-payment applies

### 2. Refer for Manual Review
Send for human review when:
- Fraud indicators detected (unusual patterns, modified documents)
- High-value claims (>₹25,000)
- Complex medical conditions
- System confidence <70%
- Member appeals automated decision
- Bill/pharmacy date is 1–7 days after prescription date (soft date mismatch)

### 3. Network vs Non-Network
- **Network providers**: Apply network discounts, cashless possible
- **Non-network**: Full payment by member, standard reimbursement

## Fraud Indicators
Watch for these red flags:
- Multiple claims from same provider on same day
- Unusually high frequency of claims
- Bills with suspicious alterations
- Diagnosis not matching age/gender
- Duplicate bills across different dates
- Provider not registered/blacklisted

## Decision Output Format
Every decision should include:
```json
{
  "claim_id": "CLM_XXXXX",
  "decision": "APPROVED/REJECTED/PARTIAL/MANUAL_REVIEW",
  "approved_amount": 0000,
  "rejection_reasons": [],
  "confidence_score": 0.95,
  "notes": "Additional observations",
  "next_steps": "What the claimant should do"
}
```

## Priority Rules
When multiple rules conflict:
1. Safety first (reject suspicious/fraudulent claims)
2. Policy exclusions override everything
3. Hard limits cannot be exceeded
4. Medical necessity is mandatory
5. When in doubt, refer for manual review