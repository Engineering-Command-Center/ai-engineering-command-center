import type { RagSource } from "./rag";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  // assistant-only fields
  sources?: RagSource[];
  confidence?: number;
  chunksRetrieved?: number;
  model?: string;
  error?: boolean;
  cached?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}
