"use client";

import { useCallback, useEffect, useState } from "react";
import type { ChatMessage, ChatSession } from "@/types/chat";
import {
  createSession,
  deleteSession,
  loadSessions,
  saveSessions,
  updateSession,
} from "@/lib/history";

export function useChatHistory() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    const stored = loadSessions();
    setSessions(stored);
  }, []);

  // Persist whenever sessions change
  useEffect(() => {
    if (sessions.length > 0) saveSessions(sessions);
  }, [sessions]);

  const activeSession = sessions.find((s) => s.id === activeId) ?? null;

  const startNewSession = useCallback((): ChatSession => {
    // Session is not fully created until the first message — we create a placeholder
    const placeholder = createSession("New conversation");
    setSessions((prev) => [placeholder, ...prev]);
    setActiveId(placeholder.id);
    return placeholder;
  }, []);

  const startSessionWithQuestion = useCallback(
    (question: string): ChatSession => {
      const session = createSession(question);
      setSessions((prev) => [session, ...prev]);
      setActiveId(session.id);
      return session;
    },
    []
  );

  const loadSession = useCallback((id: string) => {
    setActiveId(id);
  }, []);

  const updateMessages = useCallback(
    (sessionId: string, messages: ChatMessage[]) => {
      setSessions((prev) => {
        const updated = updateSession(prev, sessionId, messages);
        saveSessions(updated);
        return updated;
      });
    },
    []
  );

  const removeSession = useCallback(
    (id: string) => {
      setSessions((prev) => {
        const updated = deleteSession(prev, id);
        saveSessions(updated);
        return updated;
      });
      if (activeId === id) setActiveId(null);
    },
    [activeId]
  );

  const clearAll = useCallback(() => {
    setSessions([]);
    setActiveId(null);
    localStorage.removeItem("ecc-chat-history");
  }, []);

  return {
    sessions,
    activeSession,
    activeId,
    startNewSession,
    startSessionWithQuestion,
    loadSession,
    updateMessages,
    removeSession,
    clearAll,
  };
}
