"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { useScannedRepositories, useSyncRepositories, useDiscoverRepositories } from "@/hooks/useScanner";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { SyncStateBadge } from "@/components/scanner/SyncStatebadge";
import { SyncResultsDrawer } from "@/components/scanner/SyncResultsDrawer";
import type { SyncResponse } from "@/types/scanner";
import { formatRelativeTime } from "@/lib/utils";
import { RefreshCw, Search, GitBranch, HardDrive, Lock } from "lucide-react";

export default function ScannerPage() {
  const { data, isLoading, error } = useScannedRepositories();
  const syncMutation = useSyncRepositories();
  const discoverMutation = useDiscoverRepositories();
  const [lastSyncResult, setLastSyncResult] = useState<SyncResponse | null>(null);
  const [forceReclone, setForceReclone] = useState(false);
  const [filter, setFilter] = useState("");

  const repos = data?.repositories ?? [];
  const filtered = filter
    ? repos.filter((r) => r.name.toLowerCase().includes(filter.toLowerCase()))
    : repos;

  async function handleSync() {
    const result = await syncMutation.mutateAsync({ force_reclone: forceReclone });
    setLastSyncResult(result);
  }

  const isBusy = syncMutation.isPending || discoverMutation.isPending;

  return (
    <div>
      <Header title="Repository Scanner" />

      <div className="p-6 space-y-4">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
            <input
              className="w-full pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Filter repositories…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={forceReclone}
              onChange={(e) => setForceReclone(e.target.checked)}
              className="rounded"
            />
            Force re-clone
          </label>

          <button
            onClick={() => discoverMutation.mutate()}
            disabled={isBusy}
            className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <Search className="h-3.5 w-3.5" />
            Discover
          </button>

          <button
            onClick={handleSync}
            disabled={isBusy}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-brand-500 text-white rounded-lg hover:bg-brand-900 disabled:opacity-50 transition-colors"
          >
            {isBusy ? (
              <LoadingSpinner className="h-3.5 w-3.5" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            Sync All
          </button>
        </div>

        {/* Stats bar */}
        {data && (
          <div className="flex gap-6 text-sm text-gray-500">
            <span><strong className="text-gray-800">{data.total}</strong> total</span>
            <span><strong className="text-green-600">{data.cloned}</strong> synced</span>
            <span><strong className="text-gray-500">{data.pending}</strong> pending</span>
            {data.errored > 0 && (
              <span><strong className="text-red-600">{data.errored}</strong> errors</span>
            )}
          </div>
        )}

        {isLoading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        )}

        {error && <ErrorMessage message={error.message} />}
        {syncMutation.error && <ErrorMessage message={syncMutation.error.message} />}

        {/* Repository table */}
        {filtered.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Repository</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden md:table-cell">Branch</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden lg:table-cell">Last commit</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden lg:table-cell">Size</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden md:table-cell">Synced</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((repo) => (
                  <tr key={repo.name} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {repo.private && <Lock className="h-3 w-3 text-gray-400 shrink-0" />}
                        <div>
                          <p className="font-medium text-gray-800">{repo.name}</p>
                          {repo.language && (
                            <p className="text-xs text-gray-400">{repo.language}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="flex items-center gap-1 text-gray-500">
                        <GitBranch className="h-3 w-3" />
                        {repo.default_branch}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      {repo.last_commit_sha ? (
                        <div>
                          <p className="font-mono text-xs text-gray-500">{repo.last_commit_sha.slice(0, 8)}</p>
                          <p className="text-xs text-gray-400 truncate max-w-48">{repo.last_commit_message}</p>
                        </div>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      {repo.size_kb != null ? (
                        <span className="flex items-center gap-1 text-gray-500 text-xs">
                          <HardDrive className="h-3 w-3" />
                          {repo.size_kb >= 1024
                            ? `${(repo.size_kb / 1024).toFixed(1)} MB`
                            : `${repo.size_kb} KB`}
                        </span>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell text-xs text-gray-400">
                      {repo.last_synced_at ? formatRelativeTime(repo.last_synced_at) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <SyncStateBadge state={repo.sync_state} />
                        {repo.error_message && (
                          <p className="text-xs text-red-500 mt-1 max-w-48 truncate" title={repo.error_message}>
                            {repo.error_message}
                          </p>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!isLoading && filtered.length === 0 && !error && (
          <div className="text-center py-16 text-gray-400">
            <p className="text-sm">No repositories found.</p>
            <p className="text-xs mt-1">Click <strong>Discover</strong> to fetch repos from GitHub.</p>
          </div>
        )}
      </div>

      <SyncResultsDrawer
        result={lastSyncResult}
        onClose={() => setLastSyncResult(null)}
      />
    </div>
  );
}
