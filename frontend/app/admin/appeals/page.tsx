"use client";

import { useEffect, useState } from "react";
import { Inbox } from "lucide-react";
import { listAppeals, getAppeal, resolveAppeal } from "@/lib/api";
import type { Appeal, AppealDetail } from "@/types";
import StatusBadge from "@/components/StatusBadge";
import LoadingSpinner from "@/components/LoadingSpinner";
import FilterPills from "@/components/FilterPills";
import { PageMotion } from "@/components/motion";

const FILTERS = [
  { label: "All", value: "" },
  { label: "Pending", value: "PENDING" },
  { label: "Under Review", value: "UNDER_REVIEW" },
  { label: "Upheld", value: "UPHELD" },
  { label: "Dismissed", value: "DISMISSED" },
];

export default function AppealsPage() {
  const [appeals, setAppeals] = useState<Appeal[]>([]);
  const [filter, setFilter] = useState("PENDING");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<AppealDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [resolution, setResolution] = useState({ new_decision: "APPROVED", approved_amount: "", reviewer_notes: "" });
  const [resolveLoading, setResolveLoading] = useState(false);
  const [resolveMsg, setResolveMsg] = useState("");

  function load() {
    setLoading(true);
    listAppeals(filter || undefined)
      .then(setAppeals)
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [filter]);

  async function open(id: number) {
    setSelected(null);
    setResolveMsg("");
    setDetailLoading(true);
    const detail = await getAppeal(id);
    setSelected(detail);
    setResolution({ new_decision: "APPROVED", approved_amount: "", reviewer_notes: "" });
    setDetailLoading(false);
  }

  async function handleResolve(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) return;
    setResolveLoading(true);
    try {
      await resolveAppeal(selected.appeal.id, {
        new_decision: resolution.new_decision,
        approved_amount: parseFloat(resolution.approved_amount) || 0,
        reviewer_notes: resolution.reviewer_notes,
      });
      setResolveMsg("Appeal resolved successfully.");
      load();
    } catch (e: unknown) {
      setResolveMsg(e instanceof Error ? e.message : "Failed");
    } finally {
      setResolveLoading(false);
    }
  }

  return (
    <PageMotion>
      <div className="mb-6">
        <span className="eyebrow">Manual Review</span>
        <h1 className="page-title">
          Appeals <em>Queue</em>
        </h1>
        <p className="mt-2 text-[13px] text-ink-soft">Review and resolve claim appeals</p>
      </div>

      <div className="mb-4">
        <FilterPills options={FILTERS} value={filter} onChange={setFilter} />
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* List */}
        <div>
          {loading ? (
            <LoadingSpinner />
          ) : appeals.length === 0 ? (
            <div className="card flex flex-col items-center py-12 text-center">
              <Inbox size={28} strokeWidth={1.5} className="mb-2 text-ink-faint" />
              <p className="text-sm text-ink-soft">No appeals found.</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {appeals.map((a) => (
                <button
                  key={a.appeal_id}
                  onClick={() => open(a.appeal_id)}
                  className={`block w-full rounded-2xl border bg-ivory-card p-5 text-left transition-colors duration-200 hover:bg-ivory-hover ${
                    selected?.appeal.id === a.appeal_id ? "border-verdict-violet/50" : "border-ivory-line hover:border-verdict-violet/30"
                  }`}
                >
                  <div className="mb-2 flex items-start justify-between">
                    <span className="font-serif text-sm font-medium text-verdict-violet">{a.claim_id}</span>
                    <StatusBadge status={a.status} size="sm" />
                  </div>
                  <p className="text-sm font-semibold text-ink">{a.member_name}</p>
                  <p className="mt-1 truncate text-xs text-ink-soft">{a.appeal_reason}</p>
                  <p className="mt-1 text-xs text-ink-faint">{new Date(a.created_at).toLocaleDateString()}</p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Detail */}
        <div>
          {detailLoading && <LoadingSpinner />}
          {selected && !detailLoading && (
            <div className="card space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-serif text-lg font-medium text-ink">Appeal #{selected.appeal.id}</h2>
                <StatusBadge status={selected.appeal.status} size="sm" />
              </div>

              {selected.ai_decision && (
                <div className="space-y-1 rounded-xl bg-ivory-head p-3.5 text-sm">
                  <p className="font-medium text-ink-soft">
                    {["UPHELD", "DISMISSED"].includes(selected.appeal.status) ? "Final Decision" : "AI Decision"}
                  </p>
                  <div className="flex items-center justify-between">
                    <StatusBadge status={selected.ai_decision.decision} size="sm" />
                    <span className="font-medium text-ink tnum">₹{selected.ai_decision.approved_amount.toLocaleString("en-IN")}</span>
                  </div>
                  <p className="mt-1 text-xs text-ink-soft">{selected.ai_decision.notes}</p>
                </div>
              )}

              <div>
                <p className="label">Appeal Reason</p>
                <p className="text-sm text-ink-soft">{selected.appeal.appeal_reason}</p>
              </div>
              {selected.appeal.additional_notes && (
                <div>
                  <p className="label">Additional Notes</p>
                  <p className="text-sm text-ink-soft">{selected.appeal.additional_notes}</p>
                </div>
              )}

              {["PENDING", "UNDER_REVIEW"].includes(selected.appeal.status) && (
                <form onSubmit={handleResolve} className="space-y-3 border-t border-ivory-line2 pt-4">
                  <p className="font-medium text-ink">Resolve Appeal</p>
                  <div>
                    <label className="label">New Decision</label>
                    <select className="input" value={resolution.new_decision} onChange={(e) => setResolution({ ...resolution, new_decision: e.target.value })}>
                      <option>APPROVED</option>
                      <option>PARTIAL</option>
                      <option>REJECTED</option>
                    </select>
                  </div>
                  <div>
                    <label className="label">Approved Amount (₹)</label>
                    <input className="input tnum" type="number" min="0" required value={resolution.approved_amount} onChange={(e) => setResolution({ ...resolution, approved_amount: e.target.value })} />
                  </div>
                  <div>
                    <label className="label">Reviewer Notes</label>
                    <textarea className="input resize-none" rows={3} required value={resolution.reviewer_notes} onChange={(e) => setResolution({ ...resolution, reviewer_notes: e.target.value })} />
                  </div>
                  {resolveMsg && <p className={`text-sm ${resolveMsg.includes("success") ? "text-verdict-green" : "text-verdict-red"}`}>{resolveMsg}</p>}
                  <button type="submit" className="btn-primary w-full" disabled={resolveLoading}>
                    {resolveLoading ? "Saving…" : "Submit Resolution"}
                  </button>
                </form>
              )}

              {selected.appeal.reviewer_notes && (
                <div className="border-t border-ivory-line2 pt-4">
                  <p className="label">Reviewer Notes</p>
                  <p className="text-sm text-ink-soft">{selected.appeal.reviewer_notes}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </PageMotion>
  );
}
