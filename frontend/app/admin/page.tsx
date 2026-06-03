import Link from "next/link";

const cards = [
  { href: "/admin/appeals", icon: "⚖", title: "Appeals Queue", desc: "Review and resolve pending claim appeals" },
  { href: "/admin/policy", icon: "📋", title: "Policy Config", desc: "Edit coverage limits, waiting periods and exclusions" },
  { href: "/admin/metrics", icon: "📊", title: "Evaluation Metrics", desc: "AI accuracy dashboard and test suite runner" },
];

export default function AdminPage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800">Admin Panel</h1>
        <p className="text-sm text-slate-500 mt-1">Manage policy, appeals, and AI evaluation</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {cards.map((c) => (
          <Link key={c.href} href={c.href} className="card hover:shadow-md hover:border-plum-300 transition-all group">
            <div className="text-4xl mb-4">{c.icon}</div>
            <h2 className="text-lg font-semibold text-slate-800 group-hover:text-plum-700 mb-1">{c.title}</h2>
            <p className="text-sm text-slate-500">{c.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
