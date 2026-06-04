"use client";

import { useEffect, useState } from "react";
import { Play, ChevronDown, Check, X, Minus } from "lucide-react";
import { getMetrics, runTestSuite } from "@/lib/api";
import type { MetricsResponse, PerCaseResult } from "@/types";
import LoadingSpinner from "@/components/LoadingSpinner";
import StatusBadge from "@/components/StatusBadge";
import AnimatedNumber from "@/components/AnimatedNumber";
import { PageMotion, FadeUp } from "@/components/motion";
import { motion, AnimatePresence } from "framer-motion";

function Stat({ label, value, sub }: { label: string; value: string | number | null; sub?: string }) {
  return (
    <div className="card py-5">
      <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-faint">{label}</p>
      <p className="font-serif text-2xl font-medium text-ink tnum">{value ?? "—"}</p>
      {sub && <p className="mt-0.5 text-xs text-ink-faint">{sub}</p>}
    </div>
  );
}

function DecisionBar({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="text-ink-soft">{label.replace(/_/g, " ")}</span>
        <span className="font-medium text-ink tnum">{value} ({pct}%)</span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-ivory-line">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
    </div>
  );
}

function CaseRow({ c }: { c: PerCaseResult }) {
  const [expanded, setExpanded] = useState(false);

  const tone =
    c.is_correct === true ? { border: "border-verdict-green/30", bg: "bg-[#F1F8F4]", icon: Check, ic: "text-verdict-green" } :
    c.is_correct === false ? { border: "border-verdict-red/30", bg: "bg-[#FCF1F3]", icon: X, ic: "text-verdict-red" } :
    { border: "border-ivory-line", bg: "bg-ivory-head", icon: Minus, ic: "text-ink-faint" };
  const Icon = tone.icon;

  return (
    <div className={`rounded-xl border ${tone.border} ${tone.bg}`}>
      <div className="flex items-start justify-between gap-4 p-3.5">
        <div className="flex min-w-0 items-start gap-3">
          <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white ${tone.ic}`}>
            <Icon size={13} strokeWidth={3} />
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-serif font-medium text-ink">{c.case_id}</span>
              <span className="text-sm text-ink-soft">{c.case_name}</span>
            </div>
            {c.description && <p className="mt-0.5 text-xs text-ink-faint">{c.description}</p>}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-5 text-sm">
          <div className="text-right">
            <p className="mb-1 text-[10px] uppercase tracking-wide text-ink-faint">Ground Truth</p>
            <StatusBadge status={c.ground_truth} size="sm" />
          </div>
          <div className="text-right">
            <p className="mb-1 text-[10px] uppercase tracking-wide text-ink-faint">AI Output</p>
            {c.ai_decision ? <StatusBadge status={c.ai_decision} size="sm" /> : <span className="text-xs italic text-ink-faint">not run</span>}
          </div>
          {c.confidence_score != null && (
            <div className="text-right">
              <p className="mb-1 text-[10px] uppercase tracking-wide text-ink-faint">Confidence</p>
              <p className={`font-semibold tnum ${c.confidence_score >= 0.85 ? "text-verdict-green" : c.confidence_score >= 0.70 ? "text-verdict-amber" : "text-verdict-red"}`}>
                {(c.confidence_score * 100).toFixed(0)}%
              </p>
            </div>
          )}
          {(c.expected_amount != null || c.ai_amount != null) && (
            <div className="text-right">
              <p className="mb-1 text-[10px] uppercase tracking-wide text-ink-faint">Exp / AI</p>
              <p className="text-xs font-medium text-ink-soft tnum">
                {c.expected_amount != null ? `₹${c.expected_amount.toLocaleString()}` : "—"}
                <span className="mx-1 text-ink-faint">/</span>
                {c.ai_amount != null ? `₹${c.ai_amount.toLocaleString()}` : "—"}
              </p>
            </div>
          )}
        </div>
      </div>

      {c.rejection_reasons.length > 0 && (
        <div className="flex flex-wrap gap-2 px-3.5 pb-2.5">
          {c.rejection_reasons.map((r) => (
            <span key={r} className="rounded-full bg-verdict-red/10 px-2.5 py-0.5 font-mono text-xs text-verdict-red">{r}</span>
          ))}
        </div>
      )}

      {c.notes && (
        <div className="px-3.5 pb-2.5 text-xs text-ink-soft">
          <span className="font-medium text-ink-faint">Notes: </span>{c.notes}
        </div>
      )}

      {c.reasoning && (
        <div className="px-3.5 pb-3.5">
          <button onClick={() => setExpanded((v) => !v)} className="flex items-center gap-1 text-xs font-medium text-verdict-violet">
            <ChevronDown size={13} strokeWidth={2.5} className={`transition-transform ${expanded ? "rotate-180" : ""}`} />
            {expanded ? "Hide reasoning" : "Show reasoning"}
          </button>
          <AnimatePresence initial={false}>
            {expanded && (
              <motion.pre
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.25 }}
                className="mt-2 overflow-hidden whitespace-pre-wrap rounded-lg border border-ivory-line bg-white/80 p-2.5 font-sans text-xs leading-relaxed text-ink-soft"
              >
                {c.reasoning}
              </motion.pre>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

const DECISION_COLORS: Record<string, string> = {
  APPROVED: "#1E7A50",
  REJECTED: "#BE3247",
  PARTIAL: "#AE7317",
  MANUAL_REVIEW: "#6B56A6",
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

  const pct = (v: number | null) => (v != null ? `${(v * 100).toFixed(0)}%` : "—");

  const counts: Record<string, number> = {};
  for (const c of metrics.per_case) {
    if (c.ai_decision) counts[c.ai_decision] = (counts[c.ai_decision] ?? 0) + 1;
  }
  const countsTotal = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <PageMotion>
      <div className="mb-7 flex items-end justify-between">
        <div>
          <span className="eyebrow">Evaluation</span>
          <h1 className="page-title">
            AI <em>Metrics</em>
          </h1>
          <p className="mt-2 text-[13px] text-ink-soft">{metrics.data_source}</p>
        </div>
        <button onClick={handleRunSuite} disabled={suiteLoading} className="btn-primary">
          <Play size={15} strokeWidth={2.5} />
          {suiteLoading ? "Running…" : "Run Test Suite"}
        </button>
      </div>

      {/* Summary stats */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Test Cases" value={metrics.total_test_cases} />
        <Stat label="Results" value={`${metrics.passed} / ${metrics.evaluated}`} sub={metrics.evaluated === 0 ? "run the suite first" : "passed"} />
        <Stat label="Accuracy" value={pct(metrics.accuracy)} />
        <Stat label="Mean Amount Error" value={metrics.mean_amount_deviation != null ? `₹${metrics.mean_amount_deviation.toFixed(0)}` : null} />
      </div>

      <div className="mb-6 grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Classification */}
        <FadeUp delay={0.05}>
          <div className="card">
            <p className="section-title">Classification Metrics</p>
            <div className="space-y-1 text-sm">
              {[
                ["Precision", pct(metrics.precision)],
                ["Recall", pct(metrics.recall)],
                ["False Positive Rate", pct(metrics.false_positive_rate)],
                ["False Negative Rate", pct(metrics.false_negative_rate)],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between border-b border-ivory-line2 py-2 last:border-0">
                  <span className="text-ink-soft">{label}</span>
                  <span className="font-semibold text-ink tnum">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </FadeUp>

        {/* Breakdown */}
        <FadeUp delay={0.1}>
          <div className="card">
            <p className="section-title">AI Decisions Breakdown</p>
            {countsTotal === 0 ? (
              <p className="text-sm italic text-ink-faint">Run the test suite to see a breakdown.</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(counts).map(([k, v]) => (
                  <DecisionBar key={k} label={k} value={v} total={countsTotal} color={DECISION_COLORS[k] ?? "#A89D94"} />
                ))}
              </div>
            )}
          </div>
        </FadeUp>
      </div>

      {/* Per-case */}
      <FadeUp delay={0.15}>
        <div className="card">
          <div className="mb-4 flex items-center justify-between">
            <p className="section-title mb-0">Test Case Results</p>
            <div className="flex items-center gap-4">
              {lastRunAt && <span className="text-xs text-ink-faint">Last run: {new Date(lastRunAt).toLocaleString()}</span>}
              {metrics.evaluated > 0 && (
                <span className={`text-sm font-semibold ${metrics.passed === metrics.evaluated ? "text-verdict-green" : "text-verdict-amber"}`}>
                  {metrics.passed}/{metrics.evaluated} passed
                </span>
              )}
            </div>
          </div>

          {suiteLoading ? (
            <LoadingSpinner text="Running test cases against the live adjudication engine…" />
          ) : metrics.per_case.length === 0 ? (
            <p className="py-4 text-center text-sm italic text-ink-faint">No results yet. Click "Run Test Suite" to evaluate.</p>
          ) : (
            <div className="space-y-3">
              {metrics.per_case.map((c) => (
                <CaseRow key={c.case_id} c={c} />
              ))}
            </div>
          )}
        </div>
      </FadeUp>
    </PageMotion>
  );
}
