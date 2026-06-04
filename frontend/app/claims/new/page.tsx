"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { submitClaim } from "@/lib/api";
import DocumentUpload from "@/components/DocumentUpload";
import { PageMotion, FadeUp } from "@/components/motion";

export default function NewClaimPage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    member_id: "",
    member_name: "",
    member_join_date: "2024-01-01",
    treatment_date: "",
    claim_amount: "",
    hospital_name: "",
    cashless_request: false,
    ytd_claimed_amount: "0",
    previous_claims_same_day: "0",
    is_for_dependent: false,
    dependent_name: "",
    dependent_age: "",
    dependent_relation: "",
    sessions_claimed: "",
  });

  function set(key: string, value: string | boolean) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (files.length === 0) {
      setError("Please upload at least one document.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = {
        member_id: form.member_id,
        member_name: form.member_name,
        member_join_date: form.member_join_date,
        treatment_date: form.treatment_date,
        claim_amount: parseFloat(form.claim_amount),
        hospital_name: form.hospital_name || null,
        cashless_request: form.cashless_request,
        ytd_claimed_amount: parseFloat(form.ytd_claimed_amount),
        previous_claims_same_day: parseInt(form.previous_claims_same_day),
        dependent_name: form.is_for_dependent ? form.dependent_name || null : null,
        dependent_age: form.is_for_dependent && form.dependent_age ? parseInt(form.dependent_age) : null,
        dependent_relation: form.is_for_dependent ? form.dependent_relation || null : null,
        sessions_claimed: form.sessions_claimed ? parseInt(form.sessions_claimed) : null,
      };
      const result = await submitClaim(files, data);
      router.push(`/claims/${result.claim_id}`);
      // Keep the loading screen up while the router navigates away.
      // Resetting loading here would flash the form for a frame before
      // the route actually changes to the result page.
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Submission failed");
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col items-center justify-center py-24 text-center">
        <div className="relative mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-twilight">
          <Loader2 size={26} className="animate-spin text-white" strokeWidth={2} />
        </div>
        <h2 className="font-serif text-xl font-medium text-ink">Adjudicating your claim</h2>
        <p className="mt-2 text-sm text-ink-soft">
          Extracting documents, retrieving policy context, and reasoning through the rules…
        </p>
        <p className="mt-1 text-xs text-ink-faint">This usually takes 20–40 seconds</p>
      </div>
    );
  }

  return (
    <PageMotion className="mx-auto max-w-2xl">
      <div className="mb-7">
        <span className="eyebrow">New Submission</span>
        <h1 className="page-title">
          Submit a <em>Claim</em>
        </h1>
        <p className="mt-2 text-[13px] text-ink-soft">
          Upload medical documents and provide claim details — AI decision in ~30s
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Member details */}
        <FadeUp delay={0.05}>
          <div className="card">
            <p className="section-title">Member Details</p>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Member ID</label>
                <input className="input" required value={form.member_id} onChange={(e) => set("member_id", e.target.value)} placeholder="EMP001" />
              </div>
              <div>
                <label className="label">Member Name</label>
                <input className="input" required value={form.member_name} onChange={(e) => set("member_name", e.target.value)} placeholder="Full name" />
              </div>
              <div>
                <label className="label">Policy Join Date</label>
                <input className="input" type="date" required value={form.member_join_date} onChange={(e) => set("member_join_date", e.target.value)} />
              </div>
              <div>
                <label className="label">YTD Claimed (₹)</label>
                <input className="input tnum" type="number" min="0" value={form.ytd_claimed_amount} onChange={(e) => set("ytd_claimed_amount", e.target.value)} />
              </div>
            </div>

            <label className="mt-4 flex cursor-pointer items-center gap-2.5 text-sm text-ink">
              <input
                type="checkbox"
                className="h-4 w-4 accent-coral"
                checked={form.is_for_dependent}
                onChange={(e) => set("is_for_dependent", e.target.checked)}
              />
              This claim is for a dependent
            </label>

            {form.is_for_dependent && (
              <div className="mt-4 grid grid-cols-3 gap-4 border-t border-ivory-line2 pt-4">
                <div>
                  <label className="label">Dependent Name</label>
                  <input className="input" required={form.is_for_dependent} value={form.dependent_name} onChange={(e) => set("dependent_name", e.target.value)} placeholder="Full name" />
                </div>
                <div>
                  <label className="label">Age</label>
                  <input className="input tnum" type="number" min="0" max="120" required={form.is_for_dependent} value={form.dependent_age} onChange={(e) => set("dependent_age", e.target.value)} placeholder="26" />
                </div>
                <div>
                  <label className="label">Relation</label>
                  <select className="input" required={form.is_for_dependent} value={form.dependent_relation} onChange={(e) => set("dependent_relation", e.target.value)}>
                    <option value="">Select</option>
                    <option value="Spouse">Spouse</option>
                    <option value="Son">Son</option>
                    <option value="Daughter">Daughter</option>
                  </select>
                </div>
              </div>
            )}
          </div>
        </FadeUp>

        {/* Claim details */}
        <FadeUp delay={0.1}>
          <div className="card">
            <p className="section-title">Claim Details</p>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Treatment Date</label>
                <input className="input" type="date" required value={form.treatment_date} onChange={(e) => set("treatment_date", e.target.value)} />
              </div>
              <div>
                <label className="label">Claim Amount (₹)</label>
                <input className="input tnum" type="number" min="1" step="0.01" required value={form.claim_amount} onChange={(e) => set("claim_amount", e.target.value)} placeholder="0.00" />
              </div>
              <div>
                <label className="label">Hospital Name <span className="font-normal text-ink-faint">(optional)</span></label>
                <input className="input" value={form.hospital_name} onChange={(e) => set("hospital_name", e.target.value)} placeholder="e.g. Apollo Hospitals" />
              </div>
              <div>
                <label className="label">Same-day Claim Count</label>
                <input className="input tnum" type="number" min="0" value={form.previous_claims_same_day} onChange={(e) => set("previous_claims_same_day", e.target.value)} />
              </div>
              <div>
                <label className="label">Physiotherapy Sessions <span className="font-normal text-ink-faint">(if applicable)</span></label>
                <input className="input tnum" type="number" min="1" value={form.sessions_claimed} onChange={(e) => set("sessions_claimed", e.target.value)} placeholder="e.g. 10" />
              </div>
            </div>
            <label className="mt-4 flex cursor-pointer items-center gap-2.5 text-sm text-ink">
              <input
                type="checkbox"
                className="h-4 w-4 accent-coral"
                checked={form.cashless_request}
                onChange={(e) => set("cashless_request", e.target.checked)}
              />
              Cashless request (network hospital only)
            </label>
          </div>
        </FadeUp>

        {/* Documents */}
        <FadeUp delay={0.15}>
          <div className="card">
            <p className="section-title">Medical Documents</p>
            <p className="mb-3 text-xs text-ink-soft">Upload prescription, bills, diagnostic reports, pharmacy bills</p>
            <DocumentUpload files={files} onChange={setFiles} />
          </div>
        </FadeUp>

        {error && (
          <div className="rounded-xl border-l-4 border-verdict-red bg-[#FAE9EB] px-4 py-3 text-sm text-verdict-red">
            {error}
          </div>
        )}

        <button type="submit" className="btn-primary w-full py-3.5 text-base">
          <Sparkles size={17} strokeWidth={2} />
          Submit Claim for Adjudication
        </button>
      </form>
    </PageMotion>
  );
}
