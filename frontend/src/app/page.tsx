"use client";

import { Header } from "@/components/layout/Header";
import { GitPullRequest, BookOpen, Activity, Code2, RefreshCw } from "lucide-react";
import { StatCard } from "@/components/dashboard/StatCard";
import { useHealth } from "@/hooks/useHealth";

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return "Never";
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

function formatAbsoluteTime(isoString: string | null): string {
  if (!isoString) return "";
  return new Date(isoString).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DashboardPage() {
  const { data: health, isLoading } = useHealth();

  const lastSyncRelative = formatRelativeTime(health?.last_indexed_at ?? null);
  const lastSyncAbsolute = formatAbsoluteTime(health?.last_indexed_at ?? null);
  const indexedRepos = health?.indexed_repos ?? 0;
  const healthStatus = health?.status ?? "—";

  return (
    <div>
      <Header title="Dashboard" />
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard title="Open PRs" value="—" icon={GitPullRequest} />
          <StatCard
            title="Indexed Repos"
            value={isLoading ? "…" : String(indexedRepos)}
            icon={Code2}
          />
          <StatCard title="Knowledge Docs" value="—" icon={BookOpen} />
          <StatCard
            title="System Health"
            value={isLoading ? "…" : healthStatus === "ok" ? "Healthy" : "Degraded"}
            icon={Activity}
          />
        </div>

        {/* Last Sync Banner */}
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl px-5 py-4 flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-brand-500/10 flex items-center justify-center shrink-0">
            <RefreshCw className="h-4 w-4 text-brand-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-[var(--text-primary)]">
              Last Repository Sync
            </p>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">
              {isLoading
                ? "Loading…"
                : health?.last_indexed_at
                ? `${lastSyncAbsolute} · ${indexedRepos} repos indexed`
                : "No repos indexed yet — run the indexer to get started"}
            </p>
          </div>
          <span
            className={`text-sm font-semibold shrink-0 ${
              !health?.last_indexed_at
                ? "text-[var(--text-muted)]"
                : "text-brand-500"
            }`}
            title={lastSyncAbsolute}
          >
            {isLoading ? "…" : lastSyncRelative}
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border)] p-5">
            <h3 className="font-semibold text-[var(--text-primary)] mb-4">Recent Activity</h3>
            <p className="text-sm text-[var(--text-muted)]">No activity yet.</p>
          </div>
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border)] p-5">
            <h3 className="font-semibold text-[var(--text-primary)] mb-4">Quick Actions</h3>
            <p className="text-sm text-[var(--text-muted)]">Coming soon.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
