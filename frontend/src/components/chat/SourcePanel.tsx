"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, GitBranch, FileCode2, GitCommit } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RagSource } from "@/types/rag";

interface Props {
  sources: RagSource[];
  confidence: number;
  chunksRetrieved: number;
}

function scoreToColor(score: number) {
  if (score >= 0.80) return "text-green-500";
  if (score >= 0.60) return "text-yellow-500";
  return "text-red-400";
}

function confidenceLabel(c: number): { label: string; color: string; bg: string } {
  if (c >= 0.75) return { label: "High", color: "text-green-600 dark:text-green-400", bg: "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800" };
  if (c >= 0.50) return { label: "Medium", color: "text-yellow-600 dark:text-yellow-400", bg: "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800" };
  if (c > 0) return { label: "Low", color: "text-red-500", bg: "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800" };
  return { label: "None", color: "text-[var(--text-muted)]", bg: "bg-[var(--bg-secondary)] border-[var(--border)]" };
}

interface SourceItemProps {
  source: RagSource;
  index: number;
}

function SourceItem({ source, index }: SourceItemProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-[var(--border)] overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 px-3 py-2.5 text-left hover:bg-[var(--bg-hover)] transition-colors"
      >
        <span className="text-[11px] font-mono text-[var(--text-muted)] shrink-0 mt-0.5">[{index}]</span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-semibold text-[var(--text-primary)] truncate max-w-32">{source.repo}</span>
            <span className="text-[var(--text-muted)] text-xs">/</span>
            <span className="text-xs text-[var(--text-secondary)] truncate flex-1">{source.file_path}</span>
          </div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-[10px] bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-muted)] px-1.5 py-0.5 rounded font-mono">
              {source.language}
            </span>
            <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-0.5">
              <FileCode2 className="h-2.5 w-2.5" />
              L{source.start_line}–{source.end_line}
            </span>
            {source.commit_sha && (
              <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-0.5 font-mono">
                <GitCommit className="h-2.5 w-2.5" />
                {source.commit_sha.slice(0, 7)}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className={cn("text-xs font-mono font-medium tabular-nums", scoreToColor(source.score))}>
            {(source.score * 100).toFixed(0)}%
          </span>
          {expanded ? (
            <ChevronUp className="h-3.5 w-3.5 text-[var(--text-muted)]" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5 text-[var(--text-muted)]" />
          )}
        </div>
      </button>

      {expanded && source.excerpt && (
        <div className="border-t border-[var(--border)] px-3 py-2.5 bg-[var(--bg-secondary)]">
          <pre className="text-[11px] text-[var(--text-secondary)] font-mono whitespace-pre-wrap break-words leading-relaxed max-h-40 overflow-y-auto">
            {source.excerpt}
          </pre>
        </div>
      )}
    </div>
  );
}

export function SourcePanel({ sources, confidence, chunksRetrieved }: Props) {
  const [open, setOpen] = useState(false);
  const { label, color, bg } = confidenceLabel(confidence);

  if (sources.length === 0) return null;

  return (
    <div className="mt-3 space-y-2">
      {/* Summary bar */}
      <div className="flex items-center justify-between gap-3">
        <div className={cn("flex items-center gap-2 text-[11px] px-2.5 py-1 rounded-full border", bg)}>
          <span className={cn("font-semibold", color)}>{label} confidence</span>
          <span className="text-[var(--text-muted)]">·</span>
          <span className="text-[var(--text-muted)]">{chunksRetrieved} chunks</span>
          <span className="text-[var(--text-muted)]">·</span>
          <span className={cn("font-mono", color)}>{(confidence * 100).toFixed(0)}%</span>
        </div>

        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1 text-[11px] text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
        >
          {open ? "Hide" : `${sources.length} source${sources.length !== 1 ? "s" : ""}`}
          {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        </button>
      </div>

      {/* Source list */}
      {open && (
        <div className="space-y-2 animate-fade-in">
          {sources.map((src, i) => (
            <SourceItem key={i} source={src} index={i + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
