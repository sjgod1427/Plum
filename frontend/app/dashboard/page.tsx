"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listClaims } from "@/lib/api";
import type { ClaimListItem, Decision } from "@/types";
import ClaimsTable from "@/components/ClaimsTable";
import LoadingSpinner from "@/components/LoadingSpinner";

const FILTERS: { label: string; value: string }[] = [
  { label: "All", value: "" },
  { label: "Approved", value: "APPROVED" },
  { label: "Rejected", value: "REJECTED" },
  { label: "Partial", value: "PARTIAL" },
  { label: "Manual Review", value: "MANUAL_REVIEW" },
];

export default function DashboardPage() {
  const [claims, setClaims] = useState<ClaimListItem[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    listClaims(filter || undefined)
      .then(setClaims)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filter]);

  const breakdown = claims.reduce<Record<string, number>>((acc, c) => {
    const key = c.decision ?? c.status;
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

  const statColor: Record<string, string> = {
    APPROVED: "text-green-600",
    REJECTED: "text-red-600",
    PARTIAL: "text-orange-600",
    MANUAL_REVIEW: "text-yellow-600",
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Claims Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">All submitted OPD claims</p>
        </div>
        <Link href="/claims/new" className="btn-primary">
          + New Claim
        </Link>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {["APPROVED", "REJECTED", "PARTIAL", "MANUAL_REVIEW"].map((s) => (
          <div key={s} className="card py-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">{s.replace("_", " ")}</p>
            <p className={`text-3xl font-bold ${statColor[s]}`}>{breakdown[s] ?? 0}</p>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-4">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
              filter === f.value
                ? "bg-plum-600 text-white"
                : "bg-white text-slate-600 border border-slate-300 hover:bg-slate-50"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : error ? (
        <div className="card text-red-600 text-sm">{error}</div>
      ) : (
        <ClaimsTable claims={claims} />
      )}
    </div>
  );
}
