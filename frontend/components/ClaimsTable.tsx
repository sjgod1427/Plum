"use client";

import Link from "next/link";
import type { ClaimListItem } from "@/types";
import StatusBadge from "./StatusBadge";

interface Props {
  claims: ClaimListItem[];
}

export default function ClaimsTable({ claims }: Props) {
  if (claims.length === 0) {
    return (
      <div className="card text-center py-12 text-slate-400">
        <p className="text-4xl mb-3">📋</p>
        <p className="text-sm">No claims found. Submit your first claim to get started.</p>
      </div>
    );
  }

  return (
    <div className="card p-0 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 border-b border-slate-200">
          <tr>
            {["Claim ID", "Member", "Treatment Date", "Amount", "Decision", "Confidence", ""].map((h) => (
              <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {claims.map((c) => (
            <tr key={c.claim_id} className="hover:bg-slate-50 transition-colors">
              <td className="px-4 py-3 font-mono text-xs text-plum-600">{c.claim_id}</td>
              <td className="px-4 py-3 font-medium">{c.member_name}</td>
              <td className="px-4 py-3 text-slate-600">{c.treatment_date}</td>
              <td className="px-4 py-3 font-medium">₹{c.claim_amount.toLocaleString("en-IN")}</td>
              <td className="px-4 py-3">
                {c.decision ? (
                  <StatusBadge status={c.decision} size="sm" />
                ) : (
                  <StatusBadge status={c.status} size="sm" />
                )}
              </td>
              <td className="px-4 py-3">
                {c.confidence_score != null ? (
                  <span className="text-xs text-slate-500">{Math.round(c.confidence_score * 100)}%</span>
                ) : "—"}
              </td>
              <td className="px-4 py-3">
                <Link
                  href={`/claims/${c.claim_id}`}
                  className="text-xs text-plum-600 hover:underline font-medium"
                >
                  View →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
