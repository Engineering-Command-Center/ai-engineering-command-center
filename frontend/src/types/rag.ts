export interface RagSource {
  repo: string;
  file_path: string;
  language: string;
  start_line: number;
  end_line: number;
  score: number;
  excerpt: string;
  commit_sha: string | null;
}

export interface RagRequest {
  question: string;
  repo_filter?: string;
  language_filter?: string;
  top_k?: number;
  score_threshold?: number;
}

export interface RagResponse {
  answer: string;
  sources: RagSource[];
  confidence: number;
  chunks_retrieved: number;
  chunks_used: number;
  model: string;
}
