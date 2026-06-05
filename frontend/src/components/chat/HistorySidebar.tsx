"use client";

import { useState } from "react";
import { Plus, Trash2, MessageSquare, MoreHorizontal, BrainCircuit, Eraser } from "lucide-react";
import { cn } from "@/lib/utils";
import { groupSessionsByDate } from "@/lib/history";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import type { ChatSession } from "@/types/chat";

interface Props {
  sessions: ChatSession[];
  activeId: string | null;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onClearAll: () => void;
}

export function HistorySidebar({
  sessions,
  activeId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onClearAll,
}: Props) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const grouped = groupSessionsByDate(sessions);

  return (
    <aside className="w-64 h-screen flex flex-col border-r border-[var(--border)] bg-[var(--bg-secondary)] shrink-0">
      {/* Brand */}
      <div className="px-3 pt-4 pb-2">
        <div className="flex items-center gap-2 px-2 mb-3">
          <div className="h-7 w-7 rounded-lg bg-brand-500 flex items-center justify-center shrink-0">
            <BrainCircuit className="h-4 w-4 text-white" />
          </div>
          <span className="text-sm font-semibold text-[var(--text-primary)]">Eng Command</span>
        </div>

        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium
                     bg-brand-500 text-white hover:bg-brand-600 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New chat
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-3 py-1">
        {sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <MessageSquare className="h-8 w-8 text-[var(--text-muted)] mb-2" />
            <p className="text-xs text-[var(--text-muted)]">No conversations yet</p>
          </div>
        ) : (
          Object.entries(grouped).map(([label, group]) => (
            <div key={label} className="mb-3">
              <p className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider px-2 py-1">
                {label}
              </p>
              <div className="space-y-0.5">
                {group.map((session) => (
                  <div
                    key={session.id}
                    className={cn(
                      "group relative flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition-colors text-sm",
                      activeId === session.id
                        ? "bg-[var(--bg-tertiary)] text-[var(--text-primary)]"
                        : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                    )}
                    onClick={() => onSelectSession(session.id)}
                    onMouseEnter={() => setHoveredId(session.id)}
                    onMouseLeave={() => setHoveredId(null)}
                  >
                    <MessageSquare className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" />
                    <span className="flex-1 truncate text-[13px] leading-5">{session.title}</span>
                    {(hoveredId === session.id || activeId === session.id) && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteSession(session.id);
                        }}
                        className="shrink-0 p-0.5 rounded text-[var(--text-muted)] hover:text-red-500 transition-colors"
                        title="Delete conversation"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-2 border-t border-[var(--border)] flex items-center justify-between">
        {sessions.length > 0 && (
          <button
            onClick={onClearAll}
            className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-red-500 transition-colors px-2 py-1 rounded hover:bg-[var(--bg-hover)]"
            title="Clear all history"
          >
            <Eraser className="h-3.5 w-3.5" />
            Clear all
          </button>
        )}
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </div>
    </aside>
  );
}
