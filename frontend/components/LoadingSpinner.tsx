export default function LoadingSpinner({ text = "Loading..." }: { text?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
      <div className="w-6 h-6 border-2 border-plum-600 border-t-transparent rounded-full animate-spin" />
      <span className="text-sm">{text}</span>
    </div>
  );
}
