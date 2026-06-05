"use client";

import { useState, useRef, useEffect } from "react";
import { Header } from "@/components/layout/Header";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { SourceCard } from "@/components/rag/SourceCard";
import { ConfidenceMeter } from "@/components/rag/ConfidenceMeter";
import { useRagChat } from "@/hooks/useRag";
import type { RagResponse } from "@/types/rag";
import { Send, ChevronDown, ChevronUp, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";

interface AnswerEntry {
  question: string;
  response: RagResponse;
}

const EXAMPLE_QUESTIONS = [
  "How does payment retry work?",
  "Where is authentication handled?",
  "How are background jobs scheduled?",
  "What database migrations exist?",
];

export default function RagPage() {
  const [question, setQuestion] = useState("");
  const [repoFilter, setRepoFilter] = useState("");
  const [history, setHistory] = useState<AnswerEntry[]>([]);
  const [expandedSources, setExpandedSources] = useState<Set<number>>(new Set());
  const mutation = useRagChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  async function handleAsk() {
    const q = question.trim();
    if (!q || mutation.isPending) return;
    setQuestion("");

    const result = await mutation.mutateAsync({
      question: q,
      repo_filter: repoFilter.trim() || undefined,
      top_k: 10,
    });
    setHistory((prev) => [...prev, { question: q, response: result }]);
  }

  function toggleSources(index: number) {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      next.has(index) ? next.delete(index) : next.add(index);
      return next;
    });
  }

  return (
    <div className="flex flex-col h-screen">
      <Header title="RAG Assistant" />

      <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-4xl mx-auto w-full">
        {history.length === 0 && !mutation.isPending && (
          <div className="text-center py-12 space-y-4">
            <BookOpen className="h-10 w-10 text-gray-300 mx-auto" />
            <p className="text-gray-500 text-sm font-medium">
              Ask anything about your indexed codebase
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => setQuestion(q)}
                  className="text-xs border border-gray-200 rounded-full px-3 py-1.5 text-gray-600 hover:bg-gray-50 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {history.map((entry, i) => (
          <div key={i} className="space-y-3">
            {/* Question bubble */}
            <div className="flex justify-end">
              <div className="bg-brand-500 text-white rounded-2xl px-4 py-2.5 text-sm max-w-xl">
                {entry.question}
              </div>
            </div>

            {/* Answer card */}
            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
              <div className="p-4">
                <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
                  {entry.response.answer}
                </p>
              </div>

              {/* Stats bar */}
              <div className="px-4 py-2.5 border-t border-gray-100 bg-gray-50 flex items-center justify-between gap-4">
                <ConfidenceMeter
                  confidence={entry.response.confidence}
                  chunksRetrieved={entry.response.chunks_retrieved}
                  model={entry.response.model}
                />

                {entry.response.sources.length > 0 && (
                  <button
                    onClick={() => toggleSources(i)}
                    className="flex items-center gap-1 text-xs text-brand-500 hover:text-brand-900 shrink-0"
                  >
                    {expandedSources.has(i) ? (
                      <>Hide sources <ChevronUp className="h-3 w-3" /></>
                    ) : (
                      <>{entry.response.sources.length} sources <ChevronDown className="h-3 w-3" /></>
                    )}
                  </button>
                )}
              </div>

              {/* Sources panel */}
              {expandedSources.has(i) && entry.response.sources.length > 0 && (
                <div className="p-4 pt-0 grid grid-cols-1 md:grid-cols-2 gap-2">
                  {entry.response.sources.map((src, si) => (
                    <SourceCard key={si} source={src} index={si + 1} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {mutation.isPending && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 flex items-center gap-2">
              <LoadingSpinner className="h-4 w-4" />
              <span className="text-sm text-gray-400">Searching codebase…</span>
            </div>
          </div>
        )}

        {mutation.error && <ErrorMessage message={mutation.error.message} />}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 bg-white px-4 py-4">
        <div className="max-w-4xl mx-auto space-y-2">
          <div className="flex gap-2">
            <input
              className="w-36 border border-gray-200 rounded-lg px-3 py-2 text-xs text-gray-600 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Filter by repo…"
              value={repoFilter}
              onChange={(e) => setRepoFilter(e.target.value)}
            />
            <input
              className="flex-1 border border-gray-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Ask about your codebase…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleAsk()}
            />
            <button
              onClick={handleAsk}
              disabled={mutation.isPending || !question.trim()}
              className="bg-brand-500 text-white p-2.5 rounded-xl disabled:opacity-50 hover:bg-brand-900 transition-colors"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
