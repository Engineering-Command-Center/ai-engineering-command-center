"use client";

import { Header } from "@/components/layout/Header";
import { useHealth } from "@/hooks/useHealth";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { cn } from "@/lib/utils";
import { Zap } from "lucide-react";

export default function HealthPage() {
  const { data, isLoading, dataUpdatedAt } = useHealth();

  return (
    <div>
      <Header title="System Health" />
      <div className="p-6 space-y-6">
        {isLoading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        )}
        {data && (
          <>
            {/* Overall status */}
            <div className="flex items-center gap-3">
              <span
                className={cn(
                  "text-sm font-medium px-3 py-1 rounded-full",
                  data.status === "ok"
                    ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                )}
              >
                {data.status === "ok" ? "All systems operational" : "Degraded"}
              </span>
              <span className="text-xs text-[var(--text-muted)]">
                v{data.version} · {data.environment}
              </span>
            </div>

            {/* Services */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {data.services.map((svc) => (
                <div
                  key={svc.name}
                  className="bg-[var(--bg-primary)] rounded-xl border border-[var(--border)] p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-[var(--text-primary)] capitalize">{svc.name}</span>
                    <span
                      className={cn(
                        "h-2.5 w-2.5 rounded-full",
                        svc.status === "ok" ? "bg-green-500" : "bg-yellow-500"
                      )}
                    />
                  </div>
                  <p className="text-xs text-[var(--text-muted)]">
                    {svc.latency_ms != null ? `${svc.latency_ms}ms` : "—"}
                  </p>
                </div>
              ))}
            </div>

            {/* Token usage */}
            {data.token_usage && (
              <div className="bg-[var(--bg-primary)] rounded-xl border border-[var(--border)] p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Zap className="h-4 w-4 text-brand-500" />
                  <h2 className="font-semibold text-[var(--text-primary)] text-sm">Gemini Token Usage</h2>
                  <span className="text-[10px] text-[var(--text-muted)] ml-auto">
                    since {new Date(data.token_usage.since).toLocaleDateString()} {new Date(data.token_usage.since).toLocaleTimeString()}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <TokenStat label="Requests" value={data.token_usage.requests.toLocaleString()} />
                  <TokenStat label="Prompt Tokens" value={data.token_usage.prompt_tokens.toLocaleString()} />
                  <TokenStat label="Completion Tokens" value={data.token_usage.completion_tokens.toLocaleString()} />
                  <TokenStat
                    label="Total Tokens"
                    value={data.token_usage.total_tokens.toLocaleString()}
                    highlight
                  />
                </div>
              </div>
            )}

            <p className="text-xs text-[var(--text-muted)]">
              Last checked: {new Date(dataUpdatedAt).toLocaleTimeString()} · auto-refreshes every 30s
            </p>
          </>
        )}
      </div>
    </div>
  );
}

function TokenStat({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className={cn(
      "rounded-lg p-3",
      highlight
        ? "bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800"
        : "bg-[var(--bg-secondary)]"
    )}>
      <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-wide mb-1">{label}</p>
      <p className={cn(
        "text-lg font-bold tabular-nums",
        highlight ? "text-brand-600 dark:text-brand-400" : "text-[var(--text-primary)]"
      )}>
        {value}
      </p>
    </div>
  );
}
