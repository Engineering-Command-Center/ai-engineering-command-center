"use client";

import { User } from "lucide-react";
import { cn } from "@/lib/utils";
import { CopyButton } from "@/components/ui/CopyButton";
import { MarkdownContent } from "./MarkdownContent";
import { SourcePanel } from "./SourcePanel";
import type { ChatMessage } from "@/types/chat";

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  if (message.role === "user") {
    return (
      <div className="flex items-start gap-3 justify-end animate-fade-in">
        <div className="max-w-[85%] md:max-w-[72%]">
          <div className="bg-brand-500 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed">
            {message.content}
          </div>
        </div>
        <div className="h-7 w-7 rounded-full bg-[var(--bg-tertiary)] border border-[var(--border)] flex items-center justify-center shrink-0 mt-0.5">
          <User className="h-4 w-4 text-[var(--text-secondary)]" />
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex items-start gap-3 animate-fade-in">
      <div className="h-7 w-7 rounded-full bg-brand-500 flex items-center justify-center text-white text-[10px] font-bold shrink-0 mt-0.5">
        AI
      </div>

      <div className="flex-1 min-w-0 max-w-[85%] md:max-w-[75%]">
        {message.error ? (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-red-600 dark:text-red-400">
            {message.content}
          </div>
        ) : (
          <div className="space-y-1">
            <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-2xl rounded-tl-sm px-4 py-3">
              <MarkdownContent content={message.content} />
            </div>

            {/* Action bar */}
            <div className="flex items-center gap-1 pl-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <CopyButton text={message.content} />
              {message.model && (
                <span className="text-[10px] text-[var(--text-muted)] font-mono px-2">
                  {message.model}
                </span>
              )}
            </div>

            {/* Sources */}
            {message.sources && message.sources.length > 0 && (
              <SourcePanel
                sources={message.sources}
                confidence={message.confidence ?? 0}
                chunksRetrieved={message.chunksRetrieved ?? 0}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
