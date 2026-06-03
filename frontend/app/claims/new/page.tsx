"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { submitClaim } from "@/lib/api";
import DocumentUpload from "@/components/DocumentUpload";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function NewClaimPage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    member_id: "",
    member_name: "",
    member_join_date: "",
    treatment_date: "",
    claim_amount: "",
    hospital_name: "",
    cashless_request: false,
    ytd_claimed_amount: "0",
    previous_claims_same_day: "0",
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
        ...form,
        claim_amount: parseFloat(form.claim_amount),
        ytd_claimed_amount: parseFloat(form.ytd_claimed_amount),
        previous_claims_same_day: parseInt(form.previous_claims_same_day),
        hospital_name: form.hospital_name || null,
      };
      const result = await submitClaim(files, data);
      router.push(`/claims/${result.claim_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Submission failed");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto">
        <LoadingSpinner text="Processing claim — extracting documents and adjudicating..." />
        <p className="text-center text-xs text-slate-400 mt-2">This may take 20–40 seconds</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Submit New Claim</h1>
        <p className="text-sm text-slate-500 mt-1">Upload medical documents and provide claim details</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Member details */}
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
              <input className="input" type="number" min="0" value={form.ytd_claimed_amount} onChange={(e) => set("ytd_claimed_amount", e.target.value)} />
            </div>
          </div>
        </div>

        {/* Claim details */}
        <div className="card">
          <p className="section-title">Claim Details</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Treatment Date</label>
              <input className="input" type="date" required value={form.treatment_date} onChange={(e) => set("treatment_date", e.target.value)} />
            </div>
            <div>
              <label className="label">Claim Amount (₹)</label>
              <input className="input" type="number" min="1" step="0.01" required value={form.claim_amount} onChange={(e) => set("claim_amount", e.target.value)} placeholder="0.00" />
            </div>
            <div>
              <label className="label">Hospital Name (optional)</label>
              <input className="input" value={form.hospital_name} onChange={(e) => set("hospital_name", e.target.value)} placeholder="e.g. Apollo Hospitals" />
            </div>
            <div>
              <label className="label">Same-day Claim Count</label>
              <input className="input" type="number" min="0" value={form.previous_claims_same_day} onChange={(e) => set("previous_claims_same_day", e.target.value)} />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2">
            <input
              id="cashless"
              type="checkbox"
              className="w-4 h-4 accent-plum-600"
              checked={form.cashless_request}
              onChange={(e) => set("cashless_request", e.target.checked)}
            />
            <label htmlFor="cashless" className="text-sm text-slate-700">Cashless request (network hospital only)</label>
          </div>
        </div>

        {/* Document upload */}
        <div className="card">
          <p className="section-title">Medical Documents</p>
          <p className="text-xs text-slate-500 mb-3">Upload prescription, bills, diagnostic reports, pharmacy bills</p>
          <DocumentUpload files={files} onChange={setFiles} />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <button type="submit" className="btn-primary w-full py-3 text-base">
          Submit Claim for Adjudication
        </button>
      </form>
    </div>
  );
}
