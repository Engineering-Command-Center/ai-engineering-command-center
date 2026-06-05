import type { ChatSession, ChatMessage } from "@/types/chat";

const STORAGE_KEY = "ecc-chat-history";
const MAX_SESSIONS = 50;

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function loadSessions(): ChatSession[] {
  if (!isBrowser()) return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const sessions: ChatSession[] = JSON.parse(raw);
    // Newest first
    return sessions.sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    );
  } catch {
    return [];
  }
}

export function saveSessions(sessions: ChatSession[]): void {
  if (!isBrowser()) return;
  try {
    // Cap at MAX_SESSIONS to prevent localStorage bloat
    const trimmed = sessions
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
      .slice(0, MAX_SESSIONS);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch {
    // localStorage may be full — silently ignore
  }
}

export function createSession(firstQuestion: string): ChatSession {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    title: firstQuestion.slice(0, 60) + (firstQuestion.length > 60 ? "…" : ""),
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

export function updateSession(
  sessions: ChatSession[],
  sessionId: string,
  messages: ChatMessage[]
): ChatSession[] {
  return sessions.map((s) =>
    s.id === sessionId
      ? { ...s, messages, updatedAt: new Date().toISOString() }
      : s
  );
}

export function deleteSession(sessions: ChatSession[], sessionId: string): ChatSession[] {
  return sessions.filter((s) => s.id !== sessionId);
}

export function groupSessionsByDate(sessions: ChatSession[]): Record<string, ChatSession[]> {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday.getTime() - 86_400_000);
  const startOfWeek = new Date(startOfToday.getTime() - 7 * 86_400_000);

  const groups: Record<string, ChatSession[]> = {
    Today: [],
    Yesterday: [],
    "This week": [],
    Older: [],
  };

  for (const session of sessions) {
    const d = new Date(session.updatedAt);
    if (d >= startOfToday) groups["Today"].push(session);
    else if (d >= startOfYesterday) groups["Yesterday"].push(session);
    else if (d >= startOfWeek) groups["This week"].push(session);
    else groups["Older"].push(session);
  }

  // Remove empty groups
  return Object.fromEntries(Object.entries(groups).filter(([, v]) => v.length > 0));
}
