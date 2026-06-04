const styles: Record<string, { bg: string; text: string; dot: string }> = {
  APPROVED:      { bg: "bg-[#E7F3ED]", text: "text-verdict-green",  dot: "bg-verdict-green" },
  REJECTED:      { bg: "bg-[#FAE9EB]", text: "text-verdict-red",    dot: "bg-verdict-red" },
  PARTIAL:       { bg: "bg-[#FAF0E1]", text: "text-verdict-amber",  dot: "bg-verdict-amber" },
  MANUAL_REVIEW: { bg: "bg-[#EFEBF6]", text: "text-verdict-violet", dot: "bg-verdict-violet" },
  PENDING:       { bg: "bg-ivory-line2", text: "text-ink-soft",     dot: "bg-ink-faint" },
  PROCESSED:     { bg: "bg-[#E7F3ED]", text: "text-verdict-green",  dot: "bg-verdict-green" },
  UNDER_REVIEW:  { bg: "bg-[#EFEBF6]", text: "text-verdict-violet", dot: "bg-verdict-violet" },
  UPHELD:        { bg: "bg-[#E7F3ED]", text: "text-verdict-green",  dot: "bg-verdict-green" },
  DISMISSED:     { bg: "bg-[#FAE9EB]", text: "text-verdict-red",    dot: "bg-verdict-red" },
  ERROR:         { bg: "bg-[#FAE9EB]", text: "text-verdict-red",    dot: "bg-verdict-red" },
};

interface Props {
  status: string;
  size?: "sm" | "md" | "lg";
}

export default function StatusBadge({ status, size = "md" }: Props) {
  const s = styles[status] ?? styles.PENDING;
  const sizeClass =
    size === "sm" ? "text-[11px] px-2.5 py-1 gap-1.5" :
    size === "lg" ? "text-sm px-3.5 py-1.5 gap-2" :
    "text-xs px-3 py-1 gap-1.5";
  const dotSize = size === "lg" ? "h-1.5 w-1.5" : "h-[5px] w-[5px]";

  return (
    <span className={`inline-flex items-center rounded-md font-semibold tracking-[0.02em] ${s.bg} ${s.text} ${sizeClass}`}>
      <span className={`rounded-full ${s.dot} ${dotSize}`} />
      {status.replace(/_/g, " ")}
    </span>
  );
}
