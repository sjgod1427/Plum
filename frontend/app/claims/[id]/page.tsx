"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Scale, CheckCircle2, AlertTriangle } from "lucide-react";
import { getClaim, submitAppeal } from "@/lib/api";
import type { ClaimDetail } from "@/types";
import DecisionCard from "@/components/DecisionCard";
import StatusBadge from "@/components/StatusBadge";
import LoadingSpinner from "@/components/LoadingSpinner";
import { PageMotion, FadeUp } from "@/components/motion";

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
  if (error) return <div className="card border-l-4 border-verdict-red text-verdict-red">{error}</div>;
  if (!claim) return null;

  const canAppeal =
    ["REJECTED", "PARTIAL"].includes(claim.decision?.decision ?? "") &&
    claim.claim.status !== "UNDER_REVIEW";

  const meta = [
    { label: "Claim Amount", value: `₹${claim.claim.claim_amount.toLocaleString("en-IN")}`, num: true },
    { label: "Hospital", value: claim.claim.hospital_name ?? "Not specified" },
    { label: "Cashless", value: claim.claim.cashless_request ? "Yes" : "No" },
    { label: "Join Date", value: claim.claim.member_join_date },
    { label: "YTD Claimed", value: `₹${claim.claim.ytd_claimed_amount.toLocaleString("en-IN")}`, num: true },
    { label: "Documents", value: `${claim.documents.length} uploaded` },
  ];

  return (
    <PageMotion className="mx-auto max-w-3xl">
      {/* Breadcrumb */}
      <div className="mb-6 flex items-center gap-2 text-sm text-ink-faint">
        <Link href="/dashboard" className="transition-colors hover:text-verdict-violet">Dashboard</Link>
        <span>/</span>
        <span className="font-serif text-verdict-violet">{params.id}</span>
      </div>

      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="font-serif text-[28px] font-normal tracking-tight text-ink">{claim.claim.member_name}</h1>
          <p className="mt-1 text-sm text-ink-soft">
            {claim.claim.member_id} · Treatment: {claim.claim.treatment_date}
          </p>
        </div>
        <StatusBadge status={claim.claim.status} />
      </div>

      {/* Claim meta */}
      <FadeUp delay={0.05}>
        <div className="card mb-6">
          <div className="grid grid-cols-3 gap-5 text-sm">
            {meta.map((m) => (
              <div key={m.label}>
                <p className="text-ink-faint">{m.label}</p>
                <p className={`mt-0.5 font-semibold text-ink ${m.num ? "tnum" : ""}`}>{m.value}</p>
              </div>
            ))}
          </div>
        </div>
      </FadeUp>

      {/* Decision */}
      {claim.decision ? (
        <DecisionCard decision={claim.decision} />
      ) : (
        <div className="card text-sm text-ink-soft">Decision pending…</div>
      )}

      {/* Appeal */}
      {canAppeal && !appealSuccess && (
        <div className="mt-6">
          {!showAppeal ? (
            <button onClick={() => setShowAppeal(true)} className="btn-secondary w-full py-3">
              <Scale size={16} strokeWidth={1.8} />
              Appeal this Decision
            </button>
          ) : (
            <div className="card border-l-4 border-verdict-violet">
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
                    placeholder="Explain why you believe this decision should be reviewed…"
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
                {appealError && <p className="text-sm text-verdict-red">{appealError}</p>}
                <div className="flex gap-3">
                  <button type="submit" className="btn-primary" disabled={appealLoading}>
                    {appealLoading ? "Submitting…" : "Submit Appeal"}
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
        <div className="mt-6 flex items-center gap-2 rounded-xl border-l-4 border-verdict-green bg-[#E7F3ED] px-4 py-3 text-sm text-verdict-green">
          <CheckCircle2 size={17} strokeWidth={2} /> {appealSuccess}
        </div>
      )}

      {claim.claim.status === "UNDER_REVIEW" && (
        <div className="mt-6 flex items-center gap-2 rounded-xl border-l-4 border-verdict-amber bg-[#FAF0E1] px-4 py-3 text-sm text-verdict-amber">
          <AlertTriangle size={17} strokeWidth={2} /> This claim is currently under manual review.
        </div>
      )}
    </PageMotion>
  );
}
