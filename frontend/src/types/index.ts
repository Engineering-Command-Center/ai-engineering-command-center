export interface ServiceStatus {
  name: string;
  status: "ok" | "degraded";
  latency_ms: number | null;
  detail: string | null;
}

export interface TokenUsage {
  requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  since: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  environment: string;
  services: ServiceStatus[];
  token_usage: TokenUsage | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  history: ChatMessage[];
}

export interface ChatResponse {
  reply: string;
  model: string;
  usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number } | null;
}

export interface Repository {
  id: number;
  name: string;
  full_name: string;
  description: string | null;
  language: string | null;
  stargazers_count: number;
  open_issues_count: number;
  updated_at: string;
  html_url: string;
}

export interface PullRequest {
  id: number;
  number: number;
  title: string;
  state: string;
  author: string;
  created_at: string;
  updated_at: string;
  html_url: string;
  repo: string;
}

export interface RepositoryListResponse {
  repositories: Repository[];
  total: number;
}
