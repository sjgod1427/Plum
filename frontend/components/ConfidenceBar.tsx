"use client";

import { motion, useReducedMotion } from "framer-motion";

interface Props {
  score: number;
}

export default function ConfidenceBar({ score }: Props) {
  const reduce = useReducedMotion();
  const pct = Math.round(score * 100);

  const tone =
    score >= 0.85 ? { from: "#1E7A50", to: "#6B56A6", text: "text-verdict-green", label: "High confidence" } :
    score >= 0.70 ? { from: "#AE7317", to: "#6B56A6", text: "text-verdict-amber", label: "Moderate confidence" } :
                    { from: "#BE3247", to: "#6B56A6", text: "text-verdict-red",   label: "Low confidence" };

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className={`text-sm font-medium ${tone.text}`}>{tone.label}</span>
        <span className="text-sm font-semibold text-ink tnum">{pct}%</span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-ivory-line">
        <motion.div
          className="h-full rounded-full"
          style={{ background: `linear-gradient(90deg, ${tone.from}, ${tone.to})` }}
          initial={reduce ? false : { width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        />
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-ink-faint tnum">
        <span>0%</span>
        <span>Threshold 70%</span>
        <span>100%</span>
      </div>
    </div>
  );
}
