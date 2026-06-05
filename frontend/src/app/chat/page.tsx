"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { HistorySidebar } from "@/components/chat/HistorySidebar";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { TypingIndicator } from "@/components/chat/TypingIndicator";
import { ChatInput } from "@/components/chat/ChatInput";
import { EmptyState } from "@/components/chat/EmptyState";
import { useChatHistory } from "@/hooks/useChatHistory";
import { useRagChat } from "@/hooks/useRag";
import type { ChatMessage } from "@/types/chat";

export default function ChatPage() {
  const {
    sessions,
    activeSession,
    activeId,
    startSessionWithQuestion,
    startNewSession,
    loadSession,
    updateMessages,
    removeSession,
    clearAll,
  } = useChatHistory();

  const mutation = useRagChat();
  const [repoFilter, setRepoFilter] = useState("");
  const [pendingExample, setPendingExample] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeSession?.messages, mutation.isPending]);

  const handleSend = useCallback(
    async (question: string, filter: string) => {
      // Determine session — create a new one if none is active
      let sessionId = activeId;
      let messages: ChatMessage[] = activeSession?.messages ?? [];

      if (!sessionId) {
        const session = startSessionWithQuestion(question);
        sessionId = session.id;
        messages = [];
      }

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: question,
        timestamp: new Date().toISOString(),
      };

      const nextMessages = [...messages, userMsg];
      updateMessages(sessionId, nextMessages);

      try {
        const result = await mutation.mutateAsync({
          question,
          repo_filter: filter || undefined,
          top_k: 10,
        });

        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: result.answer,
          timestamp: new Date().toISOString(),
          sources: result.sources,
          confidence: result.confidence,
          chunksRetrieved: result.chunks_retrieved,
          model: result.model,
        };

        updateMessages(sessionId, [...nextMessages, assistantMsg]);
      } catch (err) {
        const errMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: (err as Error).message ?? "An unexpected error occurred.",
          timestamp: new Date().toISOString(),
          error: true,
        };
        updateMessages(sessionId, [...nextMessages, errMsg]);
      }

      setPendingExample("");
    },
    [activeId, activeSession, startSessionWithQuestion, updateMessages, mutation]
  );

  function handleNewChat() {
    startNewSession();
    setPendingExample("");
  }

  function handleSelectExample(q: string) {
    setPendingExample(q);
  }

  const messages = activeSession?.messages ?? [];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--bg-primary)]">
      {/* Left: History sidebar */}
      <HistorySidebar
        sessions={sessions}
        activeId={activeId}
        onNewChat={handleNewChat}
        onSelectSession={loadSession}
        onDeleteSession={removeSession}
        onClearAll={clearAll}
      />

      {/* Right: Chat area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Message thread */}
        <div
          ref={threadRef}
          className="flex-1 overflow-y-auto"
        >
          {messages.length === 0 ? (
            <EmptyState onSelect={handleSelectExample} />
          ) : (
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
              {messages.map((msg) => (
                <div key={msg.id} className="group">
                  <MessageBubble message={msg} />
                </div>
              ))}
              {mutation.isPending && <TypingIndicator />}
              <div ref={bottomRef} />
            </div>
          )}

          {/* Empty state still needs scroll-bottom anchor */}
          {messages.length === 0 && <div ref={bottomRef} />}
        </div>

        {/* Input */}
        <ChatInput
          onSend={handleSend}
          disabled={mutation.isPending}
          repoFilter={repoFilter}
          onRepoFilterChange={setRepoFilter}
          initialValue={pendingExample}
        />
      </div>
    </div>
  );
}
