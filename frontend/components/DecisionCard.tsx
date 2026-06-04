"use client";

import { useState } from "react";
import { ChevronDown, AlertTriangle, XCircle, Minus } from "lucide-react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import type { AdjudicationDecision } from "@/types";
import StatusBadge from "./StatusBadge";
import ConfidenceBar from "./ConfidenceBar";
import AnimatedNumber from "./AnimatedNumber";

interface Props {
  decision: AdjudicationDecision;
}

const VERDICT_ACCENT: Record<string, string> = {
  APPROVED: "#7BEFB0",
  REJECTED: "#FFAFB8",
  PARTIAL: "#FAD08A",
  MANUAL_REVIEW: "#C9BBF0",
};

export default function DecisionCard({ decision }: Props) {
  const [showReasoning, setShowReasoning] = useState(false);
  const reduce = useReducedMotion();
  const accent = VERDICT_ACCENT[decision.decision] ?? "#FFFFFF";

  return (
    <div className="space-y-4">
      {/* ── TWILIGHT VERDICT HERO ── */}
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="relative overflow-hidden rounded-2xl border border-white/10 bg-twilight p-7"
      >
        <div
          className="ambient-a pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full"
          style={{ background: "radial-gradient(circle, rgba(155,135,245,0.30) 0%, rgba(0,0,0,0) 70%)" }}
        />
        <div
          className="ambient-b pointer-events-none absolute -bottom-24 -left-20 h-72 w-72 rounded-full"
          style={{ background: "radial-gradient(circle, rgba(232,120,140,0.26) 0%, rgba(0,0,0,0) 70%)" }}
        />
        <div
          className="twinkle pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(1px 1px at 18% 28%, rgba(255,255,255,0.7) 50%, transparent), radial-gradient(1px 1px at 72% 22%, rgba(255,255,255,0.5) 50%, transparent), radial-gradient(1px 1px at 48% 70%, rgba(255,255,255,0.4) 50%, transparent), radial-gradient(1px 1px at 88% 58%, rgba(255,255,255,0.5) 50%, transparent)",
          }}
        />
        <div className="relative z-10 flex items-end justify-between">
          <div>
            <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/55">
              Adjudication Decision
            </p>
            <StatusBadge status={decision.decision} size="lg" />
          </div>
          <div className="text-right">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/55">
              Approved Amount
            </p>
            <AnimatedNumber
              value={decision.approved_amount}
              className="font-serif text-[40px] font-medium leading-none tnum"
              style={{ color: accent }}
              format={(n) => `₹${n.toLocaleString("en-IN")}`}
            />
          </div>
        </div>
      </motion.div>

      {/* Confidence */}
      <div className="card">
        <p className="label mb-3">AI Confidence Score</p>
        <ConfidenceBar score={decision.confidence_score} />
      </div>

      {/* Rejection reasons */}
      {decision.rejection_reasons.length > 0 && (
        <div className="card border-l-4 border-verdict-red">
          <p className="section-title flex items-center gap-2 text-verdict-red">
            <XCircle size={18} strokeWidth={2} /> Rejection Reasons
          </p>
          <ul className="space-y-1.5">
            {decision.rejection_reasons.map((r) => (
              <li key={r} className="flex items-center gap-2.5 text-sm text-ink-soft">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-verdict-red" />
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Deductions */}
      {decision.deductions.length > 0 && (
        <div className="card">
          <p className="section-title">Deductions</p>
          <div className="space-y-2">
            {decision.deductions.map((d, i) => (
              <div key={i} className="flex justify-between border-b border-ivory-line2 py-1.5 text-sm last:border-0">
                <span className="flex items-center gap-2 text-ink-soft">
                  <Minus size={14} className="text-verdict-amber" strokeWidth={2.5} />
                  {d.reason}
                </span>
                <span className="font-medium text-ink tnum">−₹{d.amount.toLocaleString("en-IN")}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fraud flags */}
      {decision.fraud_flags.length > 0 && (
        <div className="card border-l-4 border-verdict-amber">
          <p className="section-title flex items-center gap-2 text-verdict-amber">
            <AlertTriangle size={18} strokeWidth={2} /> Fraud Flags
          </p>
          <ul className="space-y-1.5">
            {decision.fraud_flags.map((f) => (
              <li key={f} className="flex items-center gap-2.5 text-sm text-ink-soft">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-verdict-amber" />
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Notes + Next Steps */}
      <div className="card">
        <p className="section-title">Notes</p>
        <p className="mb-4 text-sm leading-relaxed text-ink-soft">{decision.notes}</p>
        <p className="section-title">Next Steps</p>
        <p className="text-sm leading-relaxed text-ink-soft">{decision.next_steps}</p>
      </div>

      {/* Policy sections used */}
      {decision.policy_sections_referenced.length > 0 && (
        <div className="card">
          <p className="label mb-3">Policy Sections Referenced</p>
          <div className="flex flex-wrap gap-2">
            {decision.policy_sections_referenced.map((s) => (
              <span
                key={s}
                className="rounded-full border border-verdict-violet/30 bg-verdict-violet/10 px-3 py-1 text-xs font-medium text-verdict-violet"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Reasoning (expandable) */}
      <div className="card">
        <button
          onClick={() => setShowReasoning(!showReasoning)}
          className="flex w-full items-center justify-between text-left"
        >
          <p className="section-title mb-0">AI Reasoning</p>
          <ChevronDown
            size={18}
            strokeWidth={2}
            className={`text-ink-faint transition-transform duration-300 ${showReasoning ? "rotate-180" : ""}`}
          />
        </button>
        <AnimatePresence initial={false}>
          {showReasoning && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className="overflow-hidden"
            >
              <pre className="mt-4 whitespace-pre-wrap rounded-xl border border-ivory-line bg-ivory-head p-4 font-sans text-xs leading-relaxed text-ink-soft">
                {decision.reasoning}
              </pre>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
