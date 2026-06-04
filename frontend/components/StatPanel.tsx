"use client";

import { motion, useReducedMotion } from "framer-motion";
import AnimatedNumber from "./AnimatedNumber";

export interface Stat {
  label: string;
  value: number;
  /** dot + number color */
  tone: "green" | "red" | "amber" | "neutral";
  sub?: string;
}

const TONE: Record<Stat["tone"], string> = {
  green:   "#7BEFB0",
  red:     "#FFAFB8",
  amber:   "#FAD08A",
  neutral: "#FFFFFF",
};

/** The signature twilight gradient panel — Plum's hero palette. */
export default function StatPanel({ stats }: { stats: Stat[] }) {
  const reduce = useReducedMotion();

  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="relative overflow-hidden rounded-[18px] border border-white/10 bg-twilight p-7 mb-7"
    >
      {/* drifting ambient glows */}
      <div
        className="ambient-a pointer-events-none absolute -right-24 -top-28 h-72 w-72 rounded-full"
        style={{ background: "radial-gradient(circle, rgba(155,135,245,0.30) 0%, rgba(0,0,0,0) 70%)" }}
      />
      <div
        className="ambient-b pointer-events-none absolute -bottom-32 -left-24 h-80 w-80 rounded-full"
        style={{ background: "radial-gradient(circle, rgba(232,120,140,0.28) 0%, rgba(0,0,0,0) 70%)" }}
      />
      {/* twinkling star specks */}
      <div
        className="twinkle pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "radial-gradient(1px 1px at 20% 30%, rgba(255,255,255,0.7) 50%, transparent), radial-gradient(1px 1px at 70% 20%, rgba(255,255,255,0.5) 50%, transparent), radial-gradient(1px 1px at 45% 65%, rgba(255,255,255,0.4) 50%, transparent), radial-gradient(1px 1px at 85% 55%, rgba(255,255,255,0.5) 50%, transparent), radial-gradient(1px 1px at 30% 80%, rgba(255,255,255,0.35) 50%, transparent)",
        }}
      />
      <div className="relative z-10 grid grid-cols-2 gap-y-6 md:grid-cols-4 md:gap-y-0">
        {stats.map((s, i) => (
          <div
            key={s.label}
            className={`px-7 ${i % 4 === 0 ? "md:pl-0" : "md:border-l md:border-white/[0.07]"}`}
          >
            <div className="mb-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-white/65">
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: TONE[s.tone], boxShadow: `0 0 8px ${TONE[s.tone]}` }}
              />
              {s.label}
            </div>
            <AnimatedNumber
              value={s.value}
              className="block font-serif text-[44px] font-medium leading-none tnum"
              style={{ color: TONE[s.tone] }}
            />
            {s.sub && <div className="mt-2 text-[11px] text-white/50 tnum">{s.sub}</div>}
          </div>
        ))}
      </div>
    </motion.div>
  );
}
