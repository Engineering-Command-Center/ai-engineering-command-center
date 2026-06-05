"use client";

import { useRef, useEffect, useState, type KeyboardEvent } from "react";
import { Send, Filter, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  onSend: (question: string, repoFilter: string) => void;
  disabled: boolean;
  repoFilter: string;
  onRepoFilterChange: (v: string) => void;
  initialValue?: string;
}

export function ChatInput({ onSend, disabled, repoFilter, onRepoFilterChange, initialValue = "" }: Props) {
  const [value, setValue] = useState(initialValue);
  const [showFilterInput, setShowFilterInput] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const filterRef = useRef<HTMLInputElement>(null);

  // Populate from parent (e.g. clicking an example question)
  useEffect(() => {
    if (initialValue) {
      setValue(initialValue);
      textareaRef.current?.focus();
    }
  }, [initialValue]);

  // Auto-resize textarea
  function resize() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }

  useEffect(resize, [value]);

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const q = value.trim();
    if (!q || disabled) return;
    onSend(q, repoFilter);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function toggleFilter() {
    setShowFilterInput((v) => !v);
    if (!showFilterInput) {
      setTimeout(() => filterRef.current?.focus(), 50);
    }
  }

  return (
    <div className="px-4 py-4 bg-[var(--bg-primary)] border-t border-[var(--border)]">
      <div className="max-w-3xl mx-auto space-y-2">
        {/* Repo filter pill */}
        {repoFilter && (
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-[var(--text-muted)]">Filtering by repo:</span>
            <span className="flex items-center gap-1 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 text-xs px-2 py-0.5 rounded-full">
              {repoFilter}
              <button onClick={() => onRepoFilterChange("")} className="hover:text-brand-500">
                <X className="h-3 w-3" />
              </button>
            </span>
          </div>
        )}

        {showFilterInput && (
          <div className="flex items-center gap-2 animate-fade-in">
            <input
              ref={filterRef}
              type="text"
              placeholder="Repository name (e.g. payments-service)"
              value={repoFilter}
              onChange={(e) => onRepoFilterChange(e.target.value)}
              onKeyDown={(e) => e.key === "Escape" && setShowFilterInput(false)}
              className="flex-1 text-sm px-3 py-1.5 rounded-lg border border-[var(--border)]
                         bg-[var(--bg-secondary)] text-[var(--text-primary)]
                         placeholder-[var(--text-muted)] focus:outline-none focus:ring-2
                         focus:ring-brand-500 focus:border-transparent"
            />
            <button
              onClick={() => setShowFilterInput(false)}
              className="text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)] px-2 py-1.5"
            >
              Done
            </button>
          </div>
        )}

        {/* Input row */}
        <div className={cn(
          "flex items-end gap-2 rounded-2xl border px-3 py-2.5 transition-colors",
          "bg-[var(--bg-secondary)] border-[var(--border)]",
          "focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-500/20"
        )}>
          {/* Repo filter toggle */}
          <button
            onClick={toggleFilter}
            title="Filter by repository"
            className={cn(
              "p-1.5 rounded-lg transition-colors shrink-0 mb-0.5",
              showFilterInput || repoFilter
                ? "bg-brand-100 dark:bg-brand-900/40 text-brand-500"
                : "text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
            )}
          >
            <Filter className="h-4 w-4" />
          </button>

          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={(e) => { setValue(e.target.value); resize(); }}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your codebase… (Shift+Enter for newline)"
            disabled={disabled}
            className="flex-1 resize-none bg-transparent text-sm text-[var(--text-primary)]
                       placeholder-[var(--text-muted)] focus:outline-none leading-6
                       disabled:opacity-50 min-h-[24px]"
          />

          <button
            onClick={submit}
            disabled={disabled || !value.trim()}
            className={cn(
              "p-2 rounded-xl transition-all shrink-0 mb-0.5",
              disabled || !value.trim()
                ? "bg-[var(--bg-hover)] text-[var(--text-muted)] cursor-not-allowed"
                : "bg-brand-500 text-white hover:bg-brand-600 shadow-sm hover:shadow-brand-500/25"
            )}
          >
            <Send className="h-4 w-4" />
          </button>
        </div>

        <p className="text-center text-[10px] text-[var(--text-muted)]">
          Answers are grounded in indexed repositories only · Enter to send · Shift+Enter for newline
        </p>
      </div>
    </div>
  );
}
