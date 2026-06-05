export type RepoSyncState = "pending" | "cloning" | "syncing" | "ok" | "error" | "skipped";

export interface ScannedRepository {
  name: string;
  full_name: string;
  clone_url: string;
  ssh_url: string;
  default_branch: string;
  description: string | null;
  language: string | null;
  private: boolean;
  archived: boolean;
  local_path: string;
  sync_state: RepoSyncState;
  last_synced_at: string | null;
  last_commit_sha: string | null;
  last_commit_message: string | null;
  error_message: string | null;
  size_kb: number | null;
  is_cloned: boolean;
}

export interface RepositoryScanResponse {
  repositories: ScannedRepository[];
  total: number;
  cloned: number;
  pending: number;
  errored: number;
}

export interface SyncRequest {
  names?: string[];
  force_reclone?: boolean;
}

export interface SyncResult {
  name: string;
  state: RepoSyncState;
  duration_seconds: number;
  error: string | null;
}

export interface SyncResponse {
  total: number;
  succeeded: number;
  failed: number;
  skipped: number;
  results: SyncResult[];
  duration_seconds: number;
}
