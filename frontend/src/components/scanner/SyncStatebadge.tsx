import { cn } from "@/lib/utils";
import type { RepoSyncState } from "@/types/scanner";

const STATE_STYLES: Record<RepoSyncState, string> = {
  ok: "bg-green-100 text-green-700",
  pending: "bg-gray-100 text-gray-500",
  cloning: "bg-blue-100 text-blue-700 animate-pulse",
  syncing: "bg-blue-100 text-blue-700 animate-pulse",
  error: "bg-red-100 text-red-700",
  skipped: "bg-yellow-100 text-yellow-600",
};

const STATE_LABELS: Record<RepoSyncState, string> = {
  ok: "Synced",
  pending: "Pending",
  cloning: "Cloning…",
  syncing: "Syncing…",
  error: "Error",
  skipped: "Skipped",
};

export function SyncStateBadge({ state }: { state: RepoSyncState }) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        STATE_STYLES[state]
      )}
    >
      {STATE_LABELS[state]}
    </span>
  );
}
