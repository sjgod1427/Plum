"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getClaim, submitAppeal } from "@/lib/api";
import type { ClaimDetail } from "@/types";
import DecisionCard from "@/components/DecisionCard";
import StatusBadge from "@/components/StatusBadge";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function ClaimDetailPage({ params }: { params: { id: string } }) {
  const [claim, setClaim] = useState<ClaimDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showAppeal, setShowAppeal] = useState(false);
  const [appealReason, setAppealReason] = useState("");
  const [appealNotes, setAppealNotes] = useState("");
  const [appealLoading, setAppealLoading] = useState(false);
  const [appealSuccess, setAppealSuccess] = useState("");
  const [appealError, setAppealError] = useState("");

  useEffect(() => {
    getClaim(params.id)
      .then(setClaim)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [params.id]);

  async function handleAppeal(e: React.FormEvent) {
    e.preventDefault();
    setAppealLoading(true);
    setAppealError("");
    try {
      await submitAppeal(params.id, { appeal_reason: appealReason, additional_notes: appealNotes || undefined });
      setAppealSuccess("Appeal submitted successfully. A reviewer will assess your claim.");
      setShowAppeal(false);
    } catch (e: unknown) {
      setAppealError(e instanceof Error ? e.message : "Appeal failed");
    } finally {
      setAppealLoading(false);
    }
  }

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="card text-red-600">{error}</div>;
  if (!claim) return null;

  const canAppeal = ["REJECTED", "PARTIAL"].includes(claim.decision?.decision ?? "") && claim.claim.status !== "UNDER_REVIEW";

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
        <Link href="/dashboard" className="hover:text-plum-600">Dashboard</Link>
        <span>/</span>
        <span className="font-mono">{params.id}</span>
      </div>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">{claim.claim.member_name}</h1>
          <p className="text-sm text-slate-500 mt-1">
            {claim.claim.member_id} · Treatment: {claim.claim.treatment_date}
          </p>
        </div>
        <StatusBadge status={claim.claim.status} />
      </div>

      {/* Claim meta */}
      <div className="card mb-6">
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-slate-500">Claim Amount</p>
            <p className="font-semibold">₹{claim.claim.claim_amount.toLocaleString("en-IN")}</p>
          </div>
          <div>
            <p className="text-slate-500">Hospital</p>
            <p className="font-semibold">{claim.claim.hospital_name ?? "Not specified"}</p>
          </div>
          <div>
            <p className="text-slate-500">Cashless</p>
            <p className="font-semibold">{claim.claim.cashless_request ? "Yes" : "No"}</p>
          </div>
          <div>
            <p className="text-slate-500">Join Date</p>
            <p className="font-semibold">{claim.claim.member_join_date}</p>
          </div>
          <div>
            <p className="text-slate-500">YTD Claimed</p>
            <p className="font-semibold">₹{claim.claim.ytd_claimed_amount.toLocaleString("en-IN")}</p>
          </div>
          <div>
            <p className="text-slate-500">Documents</p>
            <p className="font-semibold">{claim.documents.length} uploaded</p>
          </div>
        </div>
      </div>

      {/* Decision */}
      {claim.decision ? (
        <DecisionCard decision={claim.decision} />
      ) : (
        <div className="card text-slate-500 text-sm">Decision pending...</div>
      )}

      {/* Appeal section */}
      {canAppeal && !appealSuccess && (
        <div className="mt-6">
          {!showAppeal ? (
            <button onClick={() => setShowAppeal(true)} className="btn-secondary w-full py-3">
              ⚖ Appeal this Decision
            </button>
          ) : (
            <div className="card border-l-4 border-plum-400">
              <p className="section-title">Submit an Appeal</p>
              <form onSubmit={handleAppeal} className="space-y-4">
                <div>
                  <label className="label">Reason for Appeal</label>
                  <textarea
                    className="input resize-none"
                    rows={3}
                    required
                    value={appealReason}
                    onChange={(e) => setAppealReason(e.target.value)}
                    placeholder="Explain why you believe this decision should be reviewed..."
                  />
                </div>
                <div>
                  <label className="label">Additional Notes (optional)</label>
                  <textarea
                    className="input resize-none"
                    rows={2}
                    value={appealNotes}
                    onChange={(e) => setAppealNotes(e.target.value)}
                  />
                </div>
                {appealError && <p className="text-sm text-red-600">{appealError}</p>}
                <div className="flex gap-3">
                  <button type="submit" className="btn-primary" disabled={appealLoading}>
                    {appealLoading ? "Submitting..." : "Submit Appeal"}
                  </button>
                  <button type="button" onClick={() => setShowAppeal(false)} className="btn-secondary">
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}

      {appealSuccess && (
        <div className="mt-6 bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm text-green-700">
          ✓ {appealSuccess}
        </div>
      )}

      {claim.claim.status === "UNDER_REVIEW" && (
        <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 text-sm text-yellow-700">
          ⚠ This claim is currently under manual review.
        </div>
      )}
    </div>
  );
}
