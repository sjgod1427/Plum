"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";
import { listClaims } from "@/lib/api";
import type { ClaimListItem } from "@/types";
import ClaimsTable from "@/components/ClaimsTable";
import LoadingSpinner from "@/components/LoadingSpinner";
import StatPanel, { type Stat } from "@/components/StatPanel";
import FilterPills from "@/components/FilterPills";
import { PageMotion, FadeUp } from "@/components/motion";

const FILTERS: { label: string; value: string }[] = [
  { label: "All", value: "" },
  { label: "Approved", value: "APPROVED" },
  { label: "Rejected", value: "REJECTED" },
  { label: "Partial", value: "PARTIAL" },
  { label: "Manual Review", value: "MANUAL_REVIEW" },
];

const TONE: Record<string, Stat["tone"]> = {
  APPROVED: "green",
  REJECTED: "red",
  PARTIAL: "amber",
  MANUAL_REVIEW: "neutral",
};

export default function DashboardPage() {
  const [allClaims, setAllClaims] = useState<ClaimListItem[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    listClaims()
      .then(setAllClaims)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const claims = filter ? allClaims.filter((c) => c.decision === filter) : allClaims;

  const breakdown = allClaims.reduce<Record<string, number>>((acc, c) => {
    const key = c.decision ?? c.status;
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

  const total = allClaims.length;
  const stats: Stat[] = ["APPROVED", "REJECTED", "PARTIAL", "MANUAL_REVIEW"].map((s) => {
    const value = breakdown[s] ?? 0;
    const pct = total > 0 ? Math.round((value / total) * 100) : 0;
    return {
      label: s.replace(/_/g, " "),
      value,
      tone: TONE[s],
      sub: `${pct}% of total`,
    };
  });

  return (
    <PageMotion>
      {/* Header */}
      <div className="mb-7 flex items-end justify-between">
        <div>
          <span className="eyebrow">Adjudication</span>
          <h1 className="page-title">
            Claims <em>Dashboard</em>
          </h1>
          <p className="mt-2 text-[13px] text-ink-soft">
            AI-powered OPD claim decisions · {total} claim{total === 1 ? "" : "s"} processed
          </p>
        </div>
        <Link href="/claims/new" className="btn-primary">
          <Plus size={16} strokeWidth={2.5} />
          New Claim
        </Link>
      </div>

      {/* Twilight stat panel */}
      <StatPanel stats={stats} />

      {/* Table block */}
      <FadeUp delay={0.15}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-serif text-lg font-medium text-ink">All Claims</h2>
          <FilterPills options={FILTERS} value={filter} onChange={setFilter} />
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : error ? (
          <div className="card border-l-4 border-verdict-red text-sm text-verdict-red">{error}</div>
        ) : (
          <ClaimsTable claims={claims} />
        )}
      </FadeUp>
    </PageMotion>
  );
}
