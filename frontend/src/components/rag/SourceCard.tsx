import { ExternalLink, GitCommit } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RagSource } from "@/types/rag";

interface Props {
  source: RagSource;
  index: number;
}

function scoreColor(score: number): string {
  if (score >= 0.85) return "bg-green-100 text-green-700";
  if (score >= 0.65) return "bg-yellow-100 text-yellow-700";
  return "bg-gray-100 text-gray-500";
}

export function SourceCard({ source, index }: Props) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs space-y-1.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="font-semibold text-gray-700">[{index}]</span>{" "}
          <span className="text-brand-500 font-medium truncate">{source.repo}</span>
          <span className="text-gray-400">/</span>
          <span className="text-gray-600 truncate">{source.file_path}</span>
        </div>
        <span className={cn("shrink-0 px-1.5 py-0.5 rounded-full font-mono text-xs", scoreColor(source.score))}>
          {source.score.toFixed(3)}
        </span>
      </div>

      <div className="flex items-center gap-3 text-gray-400">
        <span>L{source.start_line}–{source.end_line}</span>
        <span className="bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{source.language}</span>
        {source.commit_sha && (
          <span className="flex items-center gap-1">
            <GitCommit className="h-3 w-3" />
            {source.commit_sha.slice(0, 8)}
          </span>
        )}
      </div>

      {source.excerpt && (
        <pre className="bg-gray-50 rounded p-2 text-gray-600 overflow-x-auto whitespace-pre-wrap break-words max-h-28">
          {source.excerpt}
        </pre>
      )}
    </div>
  );
}
