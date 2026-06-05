import { cn } from "@/lib/utils";

interface Props {
  confidence: number;
  chunksRetrieved: number;
  model: string;
}

function confidenceLabel(c: number): { label: string; color: string } {
  if (c >= 0.75) return { label: "High confidence", color: "text-green-600" };
  if (c >= 0.50) return { label: "Medium confidence", color: "text-yellow-600" };
  if (c > 0) return { label: "Low confidence", color: "text-red-500" };
  return { label: "No context found", color: "text-gray-400" };
}

export function ConfidenceMeter({ confidence, chunksRetrieved, model }: Props) {
  const { label, color } = confidenceLabel(confidence);
  const pct = Math.round(confidence * 100);

  return (
    <div className="flex items-center gap-3 text-xs text-gray-400">
      <div className="flex items-center gap-1.5">
        <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all",
              confidence >= 0.75 ? "bg-green-500" : confidence >= 0.5 ? "bg-yellow-400" : "bg-red-400"
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className={cn("font-medium", color)}>{label}</span>
        <span>({pct}%)</span>
      </div>
      <span>·</span>
      <span>{chunksRetrieved} chunks</span>
      <span>·</span>
      <span className="font-mono">{model}</span>
    </div>
  );
}
