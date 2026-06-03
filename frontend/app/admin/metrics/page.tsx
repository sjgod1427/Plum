"use client";

import { useEffect, useState } from "react";
import { getMetrics, runTestSuite } from "@/lib/api";
import type { MetricsResponse, PerCaseResult } from "@/types";
import LoadingSpinner from "@/components/LoadingSpinner";
import StatusBadge from "@/components/StatusBadge";

function Stat({ label, value, sub }: { label: string; value: string | number | null; sub?: string }) {
  return (
    <div className="card py-4">
      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">{label}</p>
      <p className="text-2xl font-bold text-slate-800">{value ?? "—"}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function DecisionBar({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-600">{label.replace("_", " ")}</span>
        <span className="font-medium">{value} ({pct}%)</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-3">
        <div className={`${color} h-3 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function CaseRow({ c }: { c: PerCaseResult }) {
  const [expanded, setExpanded] = useState(false);

  const borderColor =
    c.is_correct === true ? "border-green-200 bg-green-50" :
    c.is_correct === false ? "border-red-200 bg-red-50" :
    "border-slate-200 bg-slate-50";

  const icon =
    c.is_correct === true ? "✓" :
    c.is_correct === false ? "✗" : "·";

  const iconColor =
    c.is_correct === true ? "text-green-600" :
    c.is_correct === false ? "text-red-500" :
    "text-slate-400";

  return (
    <div className={`rounded-lg border ${borderColor}`}>
      {/* Main row */}
      <div className="flex items-start justify-between p-3 gap-4">
        <div className="flex items-start gap-3 min-w-0">
          <span className={`text-base font-bold mt-0.5 ${iconColor}`}>{icon}</span>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-slate-800">{c.case_id}</span>
              <span className="text-slate-500 text-sm">{c.case_name}</span>
            </div>
            {c.description && (
              <p className="text-xs text-slate-400 mt-0.5">{c.description}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-5 shrink-0 text-sm">
          <div className="text-right">
            <p className="text-xs text-slate-400 mb-1">Ground Truth</p>
            <StatusBadge status={c.ground_truth} size="sm" />
          </div>

          <div className="text-right">
            <p className="text-xs text-slate-400 mb-1">AI Output</p>
            {c.ai_decision
              ? <StatusBadge status={c.ai_decision} size="sm" />
              : <span className="text-slate-400 text-xs italic">not run</span>}
          </div>

          {c.confidence_score != null && (
            <div className="text-right">
              <p className="text-xs text-slate-400 mb-1">Confidence</p>
              <p className={`font-semibold text-sm ${c.confidence_score >= 0.85 ? "text-green-600" : c.confidence_score >= 0.70 ? "text-amber-500" : "text-red-500"}`}>
                {(c.confidence_score * 100).toFixed(0)}%
              </p>
            </div>
          )}

          {(c.expected_amount != null || c.ai_amount != null) && (
            <div className="text-right">
              <p className="text-xs text-slate-400 mb-1">Exp / AI Amount</p>
              <p className="text-xs font-medium text-slate-700">
                {c.expected_amount != null ? `₹${c.expected_amount.toLocaleString()}` : "—"}
                <span className="text-slate-400 mx-1">/</span>
                {c.ai_amount != null ? `₹${c.ai_amount.toLocaleString()}` : "—"}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Rejection reasons */}
      {c.rejection_reasons.length > 0 && (
        <div className="px-3 pb-2 flex gap-2 flex-wrap">
          {c.rejection_reasons.map((r) => (
            <span key={r} className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-mono">
              {r}
            </span>
          ))}
        </div>
      )}

      {/* Notes */}
      {c.notes && (
        <div className="px-3 pb-2 text-xs text-slate-600">
          <span className="font-medium text-slate-500">Notes: </span>{c.notes}
        </div>
      )}

      {/* Reasoning toggle */}
      {c.reasoning && (
        <div className="px-3 pb-3">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
          >
            {expanded ? "▲ Hide reasoning" : "▼ Show reasoning"}
          </button>
          {expanded && (
            <pre className="mt-2 text-xs text-slate-600 bg-white/80 rounded p-2 whitespace-pre-wrap border border-slate-200 font-sans leading-relaxed">
              {c.reasoning}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

const DECISION_COLORS: Record<string, string> = {
  APPROVED: "bg-green-500",
  REJECTED: "bg-red-500",
  PARTIAL: "bg-orange-400",
  MANUAL_REVIEW: "bg-yellow-400",
};

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [suiteLoading, setSuiteLoading] = useState(false);
  const [lastRunAt, setLastRunAt] = useState<string | null>(null);

  useEffect(() => {
    getMetrics().then(setMetrics).finally(() => setLoading(false));
  }, []);

  async function handleRunSuite() {
    setSuiteLoading(true);
    try {
      const r = await runTestSuite();
      setLastRunAt(r.run_at);
      const fresh = await getMetrics();
      setMetrics(fresh);
    } finally {
      setSuiteLoading(false);
    }
  }

  if (loading) return <LoadingSpinner />;
  if (!metrics) return null;

  const pct = (v: number | null) =>
    v != null ? `${(v * 100).toFixed(0)}%` : "—";

  // Compute decision breakdown from per_case
  const counts: Record<string, number> = {};
  for (const c of metrics.per_case) {
    if (c.ai_decision) counts[c.ai_decision] = (counts[c.ai_decision] ?? 0) + 1;
  }
  const countsTotal = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Evaluation Metrics</h1>
          <p className="text-sm text-slate-500 mt-1">{metrics.data_source}</p>
        </div>
        <button onClick={handleRunSuite} disabled={suiteLoading} className="btn-primary">
          {suiteLoading ? "Running..." : "▶ Run Test Suite"}
        </button>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Stat label="Test Cases" value={metrics.total_test_cases} />
        <Stat
          label="Results"
          value={`${metrics.passed} / ${metrics.evaluated}`}
          sub={metrics.evaluated === 0 ? "run the test suite first" : "passed"}
        />
        <Stat label="Overall Accuracy" value={pct(metrics.accuracy)} />
        <Stat
          label="Mean Amount Error"
          value={metrics.mean_amount_deviation != null ? `₹${metrics.mean_amount_deviation.toFixed(0)}` : null}
        />
      </div>

      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Classification metrics */}
        <div className="card">
          <p className="section-title">Classification Metrics</p>
          <div className="space-y-2 text-sm">
            {[
              ["Precision", pct(metrics.precision)],
              ["Recall", pct(metrics.recall)],
              ["False Positive Rate", pct(metrics.false_positive_rate)],
              ["False Negative Rate", pct(metrics.false_negative_rate)],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between py-1.5 border-b border-slate-100 last:border-0">
                <span className="text-slate-500">{label}</span>
                <span className="font-semibold">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* AI decisions breakdown */}
        <div className="card">
          <p className="section-title">AI Decisions Breakdown</p>
          {countsTotal === 0 ? (
            <p className="text-sm text-slate-400 italic">Run the test suite to see a breakdown.</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(counts).map(([k, v]) => (
                <DecisionBar
                  key={k}
                  label={k}
                  value={v}
                  total={countsTotal}
                  color={DECISION_COLORS[k] ?? "bg-slate-400"}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Per-case results */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <p className="section-title mb-0">Test Case Results</p>
          <div className="flex items-center gap-4">
            {lastRunAt && (
              <span className="text-xs text-slate-400">
                Last run: {new Date(lastRunAt).toLocaleString()}
              </span>
            )}
            {metrics.evaluated > 0 && (
              <span className={`text-sm font-semibold ${metrics.passed === metrics.evaluated ? "text-green-600" : "text-amber-600"}`}>
                {metrics.passed}/{metrics.evaluated} passed
              </span>
            )}
          </div>
        </div>

        {suiteLoading ? (
          <LoadingSpinner text="Running 10 test cases against live adjudication engine..." />
        ) : metrics.per_case.length === 0 ? (
          <p className="text-sm text-slate-400 italic py-4 text-center">
            No results yet. Click "Run Test Suite" to evaluate all 10 test cases.
          </p>
        ) : (
          <div className="space-y-3">
            {metrics.per_case.map((c) => (
              <CaseRow key={c.case_id} c={c} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
