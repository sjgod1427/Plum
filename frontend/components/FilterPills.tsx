"use client";

import { motion } from "framer-motion";
import { useId } from "react";

interface Option {
  label: string;
  value: string;
}

interface Props {
  options: Option[];
  value: string;
  onChange: (value: string) => void;
}

/** Segmented filter with a sliding active indicator that animates between pills. */
export default function FilterPills({ options, value, onChange }: Props) {
  const groupId = useId();

  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((o) => {
        const active = value === o.value;
        return (
          <button
            key={o.value}
            onClick={() => onChange(o.value)}
            className={`pill border ${
              active ? "text-white border-transparent" : "text-ink-soft border-ivory-line hover:text-ink"
            }`}
          >
            {active && (
              <motion.span
                layoutId={`pill-${groupId}`}
                className="absolute inset-0 -z-10 rounded-full bg-ink"
                transition={{ type: "spring", stiffness: 380, damping: 32 }}
              />
            )}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
