"use client";

import Link from "next/link";
import { ArrowRight, Inbox } from "lucide-react";
import type { ClaimListItem } from "@/types";
import StatusBadge from "./StatusBadge";

interface Props {
  claims: ClaimListItem[];
}

function confTone(score: number) {
  return score >= 0.85 ? "text-verdict-green" : score >= 0.70 ? "text-verdict-amber" : "text-verdict-red";
}

export default function ClaimsTable({ claims }: Props) {
  if (claims.length === 0) {
    return (
      <div className="card flex flex-col items-center py-14 text-center">
        <Inbox size={32} strokeWidth={1.5} className="mb-3 text-ink-faint" />
        <p className="text-sm text-ink-soft">No claims found. Submit your first claim to get started.</p>
      </div>
    );
  }

  return (
    <div className="card-flush">
      <table className="w-full text-sm">
        <thead className="border-b border-ivory-line bg-ivory-head">
          <tr>
            {["Claim ID", "Member", "Treatment Date", "Amount", "Decision", "Confidence", ""].map((h) => (
              <th
                key={h}
                className="px-5 py-3.5 text-left text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-faint"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="stagger">
          {claims.map((c, i) => (
            <tr
              key={c.claim_id}
              className="border-b border-ivory-line2 transition-colors last:border-0 hover:bg-ivory-hover"
              style={{ "--i": i } as React.CSSProperties}
            >
              <td className="px-5 py-3.5">
                <span className="font-serif text-[13.5px] font-medium text-verdict-violet">{c.claim_id}</span>
              </td>
              <td className="px-5 py-3.5 font-semibold text-ink">{c.member_name}</td>
              <td className="px-5 py-3.5 text-ink-soft">{c.treatment_date}</td>
              <td className="px-5 py-3.5 font-medium text-ink tnum">₹{c.claim_amount.toLocaleString("en-IN")}</td>
              <td className="px-5 py-3.5">
                <StatusBadge status={c.decision ?? c.status} size="sm" />
              </td>
              <td className="px-5 py-3.5">
                {c.confidence_score != null ? (
                  <span className={`font-semibold tnum ${confTone(c.confidence_score)}`}>
                    {Math.round(c.confidence_score * 100)}%
                  </span>
                ) : (
                  <span className="text-ink-faint">—</span>
                )}
              </td>
              <td className="px-5 py-3.5">
                <Link
                  href={`/claims/${c.claim_id}`}
                  className="group inline-flex items-center gap-1 text-xs font-semibold text-verdict-violet"
                >
                  View
                  <ArrowRight size={13} strokeWidth={2} className="transition-transform group-hover:translate-x-0.5" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
