"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { Header } from "@/components/layout/Header";
import {
  Users, MessageSquare, Zap, TrendingUp, Clock, ChevronDown, ChevronUp, BarChart2,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface DailyCount { day: string; count: number; }
interface DailyUsers { day: string; users: number; }
interface Stats {
  total_queries: number;
  total_users: number;
  avg_confidence: number;
  avg_response_ms: number;
  cache_hit_rate_pct: number;
  active_days: number;
  daily_queries: DailyCount[];
  daily_active_users: DailyUsers[];
}
interface UserRow {
  email: string;
  name: string;
  total_queries: number;
  last_active: string;
  first_active: string;
  avg_confidence: number;
  cache_hits: number;
  active_days: number;
}
interface QueryRow {
  timestamp: string;
  question: string;
  repo_filter: string | null;
  confidence: number;
  chunks: number;
  cached: number;
  response_ms: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function relTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  const h = Math.floor(m / 60);
  const d = Math.floor(h / 24);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  if (h < 24) return `${h}h ago`;
  return `${d}d ago`;
}

function Bar({ value, max, color = "bg-brand-500" }: { value: number; max: number; color?: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-end gap-1 h-12">
      <div className="w-full bg-[var(--bg-tertiary)] rounded-sm flex items-end">
        <div className={`${color} rounded-sm w-full transition-all`} style={{ height: `${Math.max(pct, 2)}%` }} />
      </div>
    </div>
  );
}

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({ title, value, sub, icon: Icon, color = "text-brand-500" }: {
  title: string; value: string | number; sub?: string;
  icon: React.ElementType; color?: string;
}) {
  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide">{title}</span>
        <Icon className={`h-4 w-4 ${color}`} />
      </div>
      <p className="text-2xl font-bold text-[var(--text-primary)] font-mono">{value}</p>
      {sub && <p className="text-xs text-[var(--text-muted)] mt-1">{sub}</p>}
    </div>
  );
}

// ── User detail row ───────────────────────────────────────────────────────────

function UserDetailRow({ user }: { user: UserRow }) {
  const [open, setOpen] = useState(false);
  const { data: detail } = useQuery({
    queryKey: ["admin", "user", user.email],
    queryFn: async () => {
      const { data } = await apiClient.get(`/admin/users/${encodeURIComponent(user.email)}`);
      return data as { queries: QueryRow[]; daily_activity: DailyCount[] };
    },
    enabled: open,
  });

  return (
    <>
      <tr
        className="border-b border-[var(--border)] hover:bg-[var(--bg-tertiary)] cursor-pointer transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        <td className="px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-brand-500/10 flex items-center justify-center text-xs font-bold text-brand-500">
              {user.name[0]?.toUpperCase()}
            </div>
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)]">{user.name}</p>
              <p className="text-xs text-[var(--text-muted)]">{user.email}</p>
            </div>
          </div>
        </td>
        <td className="px-4 py-3 text-center font-mono text-sm text-[var(--text-primary)]">{user.total_queries}</td>
        <td className="px-4 py-3 text-center text-sm text-[var(--text-muted)]">{user.active_days}d</td>
        <td className="px-4 py-3 text-center">
          <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${user.avg_confidence >= 0.7 ? "bg-green-500/10 text-green-500" : "bg-yellow-500/10 text-yellow-500"}`}>
            {(user.avg_confidence * 100).toFixed(0)}%
          </span>
        </td>
        <td className="px-4 py-3 text-center text-xs text-[var(--text-muted)]">{relTime(user.last_active)}</td>
        <td className="px-4 py-3 text-center">
          {open ? <ChevronUp className="h-4 w-4 mx-auto text-[var(--text-muted)]" /> : <ChevronDown className="h-4 w-4 mx-auto text-[var(--text-muted)]" />}
        </td>
      </tr>
      {open && (
        <tr className="bg-[var(--bg-tertiary)]">
          <td colSpan={6} className="px-6 py-4">
            <p className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide mb-3">Recent Queries</p>
            {!detail ? (
              <p className="text-xs text-[var(--text-muted)]">Loading…</p>
            ) : detail.queries.length === 0 ? (
              <p className="text-xs text-[var(--text-muted)]">No queries yet.</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {detail.queries.map((q, i) => (
                  <div key={i} className="flex items-start gap-3 text-xs bg-[var(--bg-secondary)] rounded-lg px-3 py-2">
                    <span className="text-[var(--text-muted)] shrink-0 font-mono w-28">{new Date(q.timestamp).toLocaleDateString()}</span>
                    <span className="flex-1 text-[var(--text-primary)] truncate">{q.question}</span>
                    {q.repo_filter && <span className="shrink-0 bg-[var(--bg-tertiary)] text-[var(--text-muted)] px-1.5 rounded">{q.repo_filter}</span>}
                    <span className={`shrink-0 font-mono ${q.confidence >= 0.7 ? "text-green-500" : "text-yellow-500"}`}>{(q.confidence * 100).toFixed(0)}%</span>
                    {q.cached === 1 && <span className="shrink-0 text-emerald-500">⚡</span>}
                  </div>
                ))}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const { data: auth, isLoading: authLoading } = useAuth();

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["admin", "stats"],
    queryFn: async () => {
      const { data } = await apiClient.get("/admin/stats");
      return data as Stats;
    },
    enabled: !!auth?.is_admin,
    refetchInterval: 30_000,
  });

  const { data: users, isLoading: usersLoading } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: async () => {
      const { data } = await apiClient.get("/admin/users");
      return data as UserRow[];
    },
    enabled: !!auth?.is_admin,
    refetchInterval: 30_000,
  });

  if (authLoading) return <div className="min-h-screen bg-[var(--bg-primary)]" />;

  if (!auth?.is_admin) {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <p className="text-[var(--text-muted)]">Admin access required.</p>
      </div>
    );
  }

  const maxDaily = Math.max(...(stats?.daily_queries.map((d) => d.count) ?? [1]), 1);

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <Header title="Admin Dashboard" />
      <div className="p-6 space-y-6 max-w-7xl mx-auto">

        {/* Stats cards */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <StatCard title="Total Queries" value={statsLoading ? "…" : (stats?.total_queries ?? 0).toLocaleString()} icon={MessageSquare} />
          <StatCard title="Total Users" value={statsLoading ? "…" : (stats?.total_users ?? 0)} icon={Users} color="text-purple-500" />
          <StatCard title="Avg Confidence" value={statsLoading ? "…" : `${((stats?.avg_confidence ?? 0) * 100).toFixed(0)}%`} icon={TrendingUp} color="text-green-500" />
          <StatCard title="Cache Hit Rate" value={statsLoading ? "…" : `${stats?.cache_hit_rate_pct ?? 0}%`} sub="Token savings" icon={Zap} color="text-yellow-500" />
          <StatCard title="Avg Response" value={statsLoading ? "…" : `${stats?.avg_response_ms ?? 0}ms`} icon={Clock} color="text-blue-500" />
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Daily queries chart */}
          <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <BarChart2 className="h-4 w-4 text-brand-500" />
              <h3 className="font-semibold text-[var(--text-primary)] text-sm">Queries — Last 14 Days</h3>
            </div>
            {statsLoading ? (
              <div className="h-20 flex items-center justify-center text-xs text-[var(--text-muted)]">Loading…</div>
            ) : (
              <div className="flex items-end gap-1 h-20">
                {(stats?.daily_queries ?? []).map((d) => (
                  <div key={d.day} className="flex-1 flex flex-col items-center gap-1" title={`${d.day}: ${d.count} queries`}>
                    <Bar value={d.count} max={maxDaily} />
                    <span className="text-[8px] text-[var(--text-muted)] rotate-45 origin-left">{d.day.slice(5)}</span>
                  </div>
                ))}
                {(stats?.daily_queries ?? []).length === 0 && (
                  <p className="text-xs text-[var(--text-muted)] m-auto">No data yet</p>
                )}
              </div>
            )}
          </div>

          {/* DAU chart */}
          <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Users className="h-4 w-4 text-purple-500" />
              <h3 className="font-semibold text-[var(--text-primary)] text-sm">Daily Active Users — Last 7 Days</h3>
            </div>
            {statsLoading ? (
              <div className="h-20 flex items-center justify-center text-xs text-[var(--text-muted)]">Loading…</div>
            ) : (
              <div className="flex items-end gap-1 h-20">
                {(stats?.daily_active_users ?? []).map((d) => {
                  const maxDau = Math.max(...(stats?.daily_active_users.map((x) => x.users) ?? [1]), 1);
                  return (
                    <div key={d.day} className="flex-1 flex flex-col items-center gap-1" title={`${d.day}: ${d.users} users`}>
                      <Bar value={d.users} max={maxDau} color="bg-purple-500" />
                      <span className="text-[8px] text-[var(--text-muted)] rotate-45 origin-left">{d.day.slice(5)}</span>
                    </div>
                  );
                })}
                {(stats?.daily_active_users ?? []).length === 0 && (
                  <p className="text-xs text-[var(--text-muted)] m-auto">No data yet</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Users table */}
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-[var(--border)] flex items-center gap-2">
            <Users className="h-4 w-4 text-[var(--text-muted)]" />
            <h3 className="font-semibold text-[var(--text-primary)] text-sm">
              Users {users ? `(${users.length})` : ""}
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  {["User", "Queries", "Active Days", "Avg Confidence", "Last Active", ""].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide text-center first:text-left">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {usersLoading ? (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-[var(--text-muted)]">Loading…</td></tr>
                ) : (users ?? []).length === 0 ? (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-[var(--text-muted)]">No users yet</td></tr>
                ) : (
                  (users ?? []).map((u) => <UserDetailRow key={u.email} user={u} />)
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
