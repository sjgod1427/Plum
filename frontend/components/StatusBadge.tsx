import type { Decision } from "@/types";

const styles: Record<string, string> = {
  APPROVED:      "bg-green-100 text-green-800 border-green-300",
  REJECTED:      "bg-red-100 text-red-800 border-red-300",
  PARTIAL:       "bg-orange-100 text-orange-800 border-orange-300",
  MANUAL_REVIEW: "bg-yellow-100 text-yellow-800 border-yellow-300",
  PENDING:       "bg-slate-100 text-slate-600 border-slate-300",
  PROCESSED:     "bg-blue-100 text-blue-800 border-blue-300",
  UNDER_REVIEW:  "bg-purple-100 text-purple-800 border-purple-300",
  ERROR:         "bg-red-100 text-red-700 border-red-300",
};

const icons: Record<string, string> = {
  APPROVED:      "✓",
  REJECTED:      "✗",
  PARTIAL:       "◑",
  MANUAL_REVIEW: "⚠",
  PENDING:       "…",
  PROCESSED:     "●",
  UNDER_REVIEW:  "⟳",
  ERROR:         "!",
};

interface Props {
  status: string;
  size?: "sm" | "md" | "lg";
}

export default function StatusBadge({ status, size = "md" }: Props) {
  const cls = styles[status] ?? "bg-slate-100 text-slate-600 border-slate-300";
  const icon = icons[status] ?? "?";
  const sizeClass = size === "sm" ? "text-xs px-2 py-0.5" : size === "lg" ? "text-base px-4 py-1.5" : "text-sm px-3 py-1";

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${cls} ${sizeClass}`}>
      <span>{icon}</span>
      {status.replace("_", " ")}
    </span>
  );
}
