export type Decision = "APPROVED" | "REJECTED" | "PARTIAL" | "MANUAL_REVIEW";
export type ClaimStatus = "PENDING" | "PROCESSED" | "ERROR" | "UNDER_REVIEW";
export type AppealStatus = "PENDING" | "UNDER_REVIEW" | "UPHELD" | "DISMISSED";

export interface Deduction {
  reason: string;
  amount: number;
}

export interface AdjudicationDecision {
  claim_id: string;
  reasoning: string;
  decision: Decision;
  approved_amount: number;
  rejection_reasons: string[];
  deductions: Deduction[];
  confidence_score: number;
  fraud_flags: string[];
  policy_sections_referenced: string[];
  notes: string;
  next_steps: string;
  created_at?: string;
}

export interface ExtractedData {
  merged_diagnosis: string;
  merged_total: number;
  all_required_docs_present: boolean;
  missing_docs: string[];
  date_consistent: boolean;
  patient_name_consistent: boolean;
}

export interface ClaimResponse {
  claim_id: string;
  status: ClaimStatus;
  decision: AdjudicationDecision;
  extracted_data: ExtractedData;
}

export interface ClaimListItem {
  claim_id: string;
  member_name: string;
  treatment_date: string;
  claim_amount: number;
  status: ClaimStatus;
  decision: Decision | null;
  approved_amount: number | null;
  confidence_score: number | null;
  created_at: string;
}

export interface ClaimDetail {
  claim: {
    id: string;
    member_id: string;
    member_name: string;
    member_join_date: string;
    treatment_date: string;
    claim_amount: number;
    hospital_name: string | null;
    cashless_request: boolean;
    ytd_claimed_amount: number;
    previous_claims_same_day: number;
    status: ClaimStatus;
    created_at: string;
  };
  decision: AdjudicationDecision | null;
  documents: {
    id: number;
    doc_type: string;
    file_path: string;
    extracted_data: Record<string, unknown>;
    created_at: string;
  }[];
}

export interface Appeal {
  appeal_id: number;
  claim_id: string;
  member_name: string | null;
  claim_amount: number | null;
  ai_decision: Decision | null;
  appeal_reason: string;
  additional_notes: string | null;
  status: AppealStatus;
  created_at: string;
  resolved_at: string | null;
}

export interface AppealDetail {
  appeal: {
    id: number;
    claim_id: string;
    appeal_reason: string;
    additional_notes: string | null;
    status: AppealStatus;
    reviewer_notes: string | null;
    created_at: string;
    resolved_at: string | null;
  };
  claim: ClaimDetail["claim"] | null;
  ai_decision: {
    decision: Decision;
    approved_amount: number;
    rejection_reasons: string[];
    notes: string;
  } | null;
}

export interface PolicyResponse {
  source: "file" | "database";
  policy: Record<string, unknown>;
}

export interface PerCaseResult {
  case_id: string;
  case_name: string;
  description: string;
  claim_id: string;
  ground_truth: string;
  expected_amount: number | null;
  ai_decision: string | null;
  ai_amount: number | null;
  confidence_score: number | null;
  is_correct: boolean | null;
  reasoning: string | null;
  notes: string | null;
  rejection_reasons: string[];
}

export interface MetricsResponse {
  total_test_cases: number;
  evaluated: number;
  passed: number;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  false_positive_rate: number | null;
  false_negative_rate: number | null;
  mean_amount_deviation: number | null;
  data_source: string;
  per_case: PerCaseResult[];
}

export interface TestSuiteResult {
  total: number;
  passed: number;
  failed: number;
  run_at: string;
  results: {
    case_id: string;
    case_name: string;
    passed: boolean;
    ground_truth?: string;
    ai_decision?: string;
    expected_amount?: number;
    actual_amount?: number;
    confidence_score?: number;
    claim_id?: string;
    error?: string;
  }[];
}
