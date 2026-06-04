import { Loader2 } from "lucide-react";

export default function LoadingSpinner({ text = "Loading…" }: { text?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-ink-soft">
      <Loader2 size={20} className="animate-spin text-coral" strokeWidth={2} />
      <span className="text-sm">{text}</span>
    </div>
  );
}
