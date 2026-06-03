"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  { label: "Submit Claim", href: "/claims/new", icon: "+" },
  { label: "Dashboard", href: "/dashboard", icon: "▦" },
  { divider: true },
  { label: "Admin", href: "/admin", icon: "⚙", header: true },
  { label: "Appeals Queue", href: "/admin/appeals", icon: "⚖" },
  { label: "Policy Config", href: "/admin/policy", icon: "📋" },
  { label: "Metrics", href: "/admin/metrics", icon: "📊" },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-plum-900 text-white flex flex-col">
      <div className="px-6 py-5 border-b border-plum-700">
        <div className="text-2xl font-bold tracking-tight">🫐 Plum</div>
        <div className="text-xs text-plum-300 mt-0.5">Claims Adjudication</div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {nav.map((item, i) => {
          if ("divider" in item && item.divider) {
            return <div key={i} className="my-3 border-t border-plum-700" />;
          }
          const active = path === item.href || (item.href !== "/" && path.startsWith(item.href ?? ""));
          return (
            <Link
              key={item.href}
              href={item.href!}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-plum-600 text-white font-medium"
                  : "text-plum-200 hover:bg-plum-800 hover:text-white"
              }`}
            >
              <span className="w-4 text-center">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-6 py-4 border-t border-plum-700 text-xs text-plum-400">
        v1.0.0 · AI-Powered
      </div>
    </aside>
  );
}
