"use client";

import { useEffect, useState } from "react";
import { listAppeals, getAppeal, resolveAppeal } from "@/lib/api";
import type { Appeal, AppealDetail } from "@/types";
import StatusBadge from "@/components/StatusBadge";
import LoadingSpinner from "@/components/LoadingSpinner";

const FILTERS = ["", "PENDING", "UNDER_REVIEW", "UPHELD", "DISMISSED"];

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
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-2">Appeals Queue</h1>
      <p className="text-sm text-slate-500 mb-6">Review and resolve claim appeals</p>

      <div className="flex gap-2 mb-4">
        {FILTERS.map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${filter === f ? "bg-plum-600 text-white" : "bg-white text-slate-600 border border-slate-300 hover:bg-slate-50"}`}>
            {f || "All"}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Left: list */}
        <div>
          {loading ? <LoadingSpinner /> : appeals.length === 0 ? (
            <div className="card text-center py-10 text-slate-400 text-sm">No appeals found.</div>
          ) : (
            <div className="space-y-2">
              {appeals.map((a) => (
                <div key={a.appeal_id} onClick={() => open(a.appeal_id)}
                  className={`card cursor-pointer hover:border-plum-300 transition-all ${selected?.appeal.id === a.appeal_id ? "border-plum-400" : ""}`}>
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-mono text-xs text-plum-600">{a.claim_id}</span>
                    <StatusBadge status={a.status} size="sm" />
                  </div>
                  <p className="font-medium text-sm">{a.member_name}</p>
                  <p className="text-xs text-slate-500 mt-1 truncate">{a.appeal_reason}</p>
                  <p className="text-xs text-slate-400 mt-1">{new Date(a.created_at).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: detail */}
        <div>
          {detailLoading && <LoadingSpinner />}
          {selected && !detailLoading && (
            <div className="card space-y-4">
              <div className="flex justify-between items-center">
                <h2 className="font-semibold">Appeal #{selected.appeal.id}</h2>
                <StatusBadge status={selected.appeal.status} size="sm" />
              </div>

              {selected.ai_decision && (
                <div className="bg-slate-50 rounded-lg p-3 text-sm space-y-1">
                  <p className="font-medium text-slate-700">
                    {["UPHELD", "DISMISSED"].includes(selected.appeal.status) ? "Final Decision" : "AI Decision"}
                  </p>
                  <div className="flex justify-between">
                    <StatusBadge status={selected.ai_decision.decision} size="sm" />
                    <span className="font-medium">₹{selected.ai_decision.approved_amount.toLocaleString("en-IN")}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{selected.ai_decision.notes}</p>
                </div>
              )}

              <div>
                <p className="label">Appeal Reason</p>
                <p className="text-sm text-slate-600">{selected.appeal.appeal_reason}</p>
              </div>
              {selected.appeal.additional_notes && (
                <div>
                  <p className="label">Additional Notes</p>
                  <p className="text-sm text-slate-600">{selected.appeal.additional_notes}</p>
                </div>
              )}

              {["PENDING", "UNDER_REVIEW"].includes(selected.appeal.status) && (
                <form onSubmit={handleResolve} className="space-y-3 border-t pt-4">
                  <p className="font-medium text-sm">Resolve Appeal</p>
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
                    <input className="input" type="number" min="0" required value={resolution.approved_amount} onChange={(e) => setResolution({ ...resolution, approved_amount: e.target.value })} />
                  </div>
                  <div>
                    <label className="label">Reviewer Notes</label>
                    <textarea className="input resize-none" rows={3} required value={resolution.reviewer_notes} onChange={(e) => setResolution({ ...resolution, reviewer_notes: e.target.value })} />
                  </div>
                  {resolveMsg && <p className={`text-sm ${resolveMsg.includes("success") ? "text-green-600" : "text-red-600"}`}>{resolveMsg}</p>}
                  <button type="submit" className="btn-primary w-full" disabled={resolveLoading}>
                    {resolveLoading ? "Saving..." : "Submit Resolution"}
                  </button>
                </form>
              )}

              {selected.appeal.reviewer_notes && (
                <div className="border-t pt-4">
                  <p className="label">Reviewer Notes</p>
                  <p className="text-sm text-slate-600">{selected.appeal.reviewer_notes}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
