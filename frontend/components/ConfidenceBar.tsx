interface Props {
  score: number;
}

export default function ConfidenceBar({ score }: Props) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.85 ? "bg-green-500" :
    score >= 0.70 ? "bg-yellow-500" :
    "bg-red-500";

  const label =
    score >= 0.85 ? "High confidence" :
    score >= 0.70 ? "Moderate confidence" :
    "Low confidence";

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-slate-600">{label}</span>
        <span className="text-sm font-semibold text-slate-800">{pct}%</span>
      </div>
      <div className="w-full bg-slate-200 rounded-full h-2.5">
        <div
          className={`${color} h-2.5 rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between mt-0.5 text-xs text-slate-400">
        <span>0%</span>
        <span>Threshold 70%</span>
        <span>100%</span>
      </div>
    </div>
  );
}
