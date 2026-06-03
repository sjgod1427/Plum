"use client";

import { useState } from "react";
import type { AdjudicationDecision } from "@/types";
import StatusBadge from "./StatusBadge";
import ConfidenceBar from "./ConfidenceBar";

interface Props {
  decision: AdjudicationDecision;
}

export default function DecisionCard({ decision }: Props) {
  const [showReasoning, setShowReasoning] = useState(false);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="card flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500 mb-1">Adjudication Decision</p>
          <StatusBadge status={decision.decision} size="lg" />
        </div>
        <div className="text-right">
          <p className="text-sm text-slate-500 mb-1">Approved Amount</p>
          <p className="text-3xl font-bold text-slate-800">
            ₹{decision.approved_amount.toLocaleString("en-IN")}
          </p>
        </div>
      </div>

      {/* Confidence */}
      <div className="card">
        <p className="label mb-3">AI Confidence Score</p>
        <ConfidenceBar score={decision.confidence_score} />
      </div>

      {/* Rejection reasons */}
      {decision.rejection_reasons.length > 0 && (
        <div className="card border-l-4 border-red-400">
          <p className="section-title text-red-700">Rejection Reasons</p>
          <ul className="space-y-1">
            {decision.rejection_reasons.map((r) => (
              <li key={r} className="flex items-center gap-2 text-sm text-red-700">
                <span className="w-2 h-2 bg-red-400 rounded-full" />
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
              <div key={i} className="flex justify-between text-sm py-1 border-b border-slate-100 last:border-0">
                <span className="text-slate-600">{d.reason}</span>
                <span className="font-medium text-slate-800">−₹{d.amount.toLocaleString("en-IN")}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fraud flags */}
      {decision.fraud_flags.length > 0 && (
        <div className="card border-l-4 border-yellow-400">
          <p className="section-title text-yellow-700">Fraud Flags</p>
          <ul className="space-y-1">
            {decision.fraud_flags.map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm text-yellow-700">
                <span>⚠</span> {f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Notes + Next Steps */}
      <div className="card">
        <p className="section-title">Notes</p>
        <p className="text-sm text-slate-600 mb-4">{decision.notes}</p>
        <p className="section-title">Next Steps</p>
        <p className="text-sm text-slate-600">{decision.next_steps}</p>
      </div>

      {/* Policy sections used */}
      {decision.policy_sections_referenced.length > 0 && (
        <div className="card">
          <p className="label mb-2">Policy Sections Referenced</p>
          <div className="flex flex-wrap gap-2">
            {decision.policy_sections_referenced.map((s) => (
              <span key={s} className="text-xs bg-plum-100 text-plum-700 px-2 py-0.5 rounded-full">
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
          className="flex items-center justify-between w-full text-left"
        >
          <p className="section-title mb-0">AI Reasoning</p>
          <span className="text-slate-400 text-sm">{showReasoning ? "▲ Hide" : "▼ Show"}</span>
        </button>
        {showReasoning && (
          <pre className="mt-4 text-xs text-slate-600 bg-slate-50 p-4 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono">
            {decision.reasoning}
          </pre>
        )}
      </div>
    </div>
  );
}
