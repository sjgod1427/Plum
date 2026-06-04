"use client";

import Link from "next/link";
import { Scale, FileCog, BarChart3, ArrowRight } from "lucide-react";
import { PageMotion, FadeUp } from "@/components/motion";

const cards = [
  { href: "/admin/appeals", icon: Scale, title: "Appeals Queue", desc: "Review and resolve pending claim appeals" },
  { href: "/admin/policy", icon: FileCog, title: "Policy Config", desc: "Edit coverage limits, waiting periods and exclusions" },
  { href: "/admin/metrics", icon: BarChart3, title: "Evaluation Metrics", desc: "AI accuracy dashboard and test suite runner" },
];

export default function AdminPage() {
  return (
    <PageMotion>
      <div className="mb-8">
        <span className="eyebrow">Control Room</span>
        <h1 className="page-title">
          Admin <em>Panel</em>
        </h1>
        <p className="mt-2 text-[13px] text-ink-soft">Manage policy, appeals, and AI evaluation</p>
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        {cards.map((c, i) => {
          const Icon = c.icon;
          return (
            <FadeUp key={c.href} delay={0.05 * i}>
              <Link
                href={c.href}
                className="group block h-full rounded-2xl border border-ivory-line bg-ivory-card p-6 transition-colors duration-200 hover:border-verdict-violet/40 hover:bg-ivory-hover"
              >
                <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-twilight text-white">
                  <Icon size={20} strokeWidth={1.8} />
                </div>
                <h2 className="mb-1 flex items-center gap-1.5 font-serif text-lg font-medium text-ink">
                  {c.title}
                  <ArrowRight size={16} className="text-ink-faint transition-transform group-hover:translate-x-1 group-hover:text-verdict-violet" strokeWidth={2} />
                </h2>
                <p className="text-sm text-ink-soft">{c.desc}</p>
              </Link>
            </FadeUp>
          );
        })}
      </div>
    </PageMotion>
  );
}
