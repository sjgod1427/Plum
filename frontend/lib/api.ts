import type {
  Appeal,
  AppealDetail,
  ClaimDetail,
  ClaimListItem,
  ClaimResponse,
  MetricsResponse,
  PolicyResponse,
  TestSuiteResult,
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ─── Claims ───────────────────────────────────────────────────────────────────

export async function submitClaim(files: File[], data: Record<string, unknown>): Promise<ClaimResponse> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  form.append("data", JSON.stringify(data));
  return request<ClaimResponse>("/claims", { method: "POST", body: form });
}

export async function listClaims(status?: string): Promise<ClaimListItem[]> {
  const qs = status ? `?status=${status}` : "";
  return request<ClaimListItem[]>(`/claims${qs}`);
}

export async function getClaim(id: string): Promise<ClaimDetail> {
  return request<ClaimDetail>(`/claims/${id}`);
}

export async function getDecision(id: string) {
  return request(`/claims/${id}/decision`);
}

// ─── Appeals ─────────────────────────────────────────────────────────────────

export async function submitAppeal(
  claimId: string,
  body: { appeal_reason: string; additional_notes?: string }
) {
  return request(`/claims/${claimId}/appeal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function listAppeals(status?: string): Promise<Appeal[]> {
  const qs = status ? `?status=${status}` : "";
  return request<Appeal[]>(`/appeals${qs}`);
}

export async function getAppeal(id: number): Promise<AppealDetail> {
  return request<AppealDetail>(`/appeals/${id}`);
}

export async function resolveAppeal(
  id: number,
  body: { new_decision: string; approved_amount: number; reviewer_notes: string }
) {
  return request(`/appeals/${id}/resolve`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ─── Admin — Policy ───────────────────────────────────────────────────────────

export async function getPolicy(): Promise<PolicyResponse> {
  return request<PolicyResponse>("/admin/policy");
}

export async function updatePolicySection(section: string, config: Record<string, unknown>) {
  return request(`/admin/policy/${section}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config, updated_by: "admin" }),
  });
}

export async function rebuildRag() {
  return request("/admin/policy/rebuild-rag", { method: "POST" });
}

// ─── Admin — Config (notifications) ──────────────────────────────────────────

export async function getAdminConfig(): Promise<{ reviewer_email: string }> {
  return request<{ reviewer_email: string }>("/admin/config");
}

export async function updateAdminConfig(reviewer_email: string) {
  return request("/admin/config", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_email }),
  });
}

// ─── Admin — Metrics ──────────────────────────────────────────────────────────

export async function getMetrics(): Promise<MetricsResponse> {
  return request<MetricsResponse>("/admin/metrics");
}

export async function runTestSuite(): Promise<TestSuiteResult> {
  return request<TestSuiteResult>("/admin/metrics/run-test-suite", { method: "POST" });
}

export async function labelClaim(
  claimId: string,
  body: { ground_truth_decision: string; actual_approved_amount?: number }
) {
  return request(`/admin/metrics/${claimId}/label`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
