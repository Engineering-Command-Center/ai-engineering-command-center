"use client";

import { X, CheckCircle2, XCircle, Clock } from "lucide-react";
import type { SyncResponse } from "@/types/scanner";
import { cn } from "@/lib/utils";

interface Props {
  result: SyncResponse | null;
  onClose: () => void;
}

export function SyncResultsDrawer({ result, onClose }: Props) {
  if (!result) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white shadow-2xl border-l border-gray-200 flex flex-col z-50">
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
        <div>
          <h3 className="font-semibold text-gray-800">Sync Results</h3>
          <p className="text-xs text-gray-400 mt-0.5">
            {result.duration_seconds}s · {result.succeeded}/{result.total} succeeded
          </p>
        </div>
        <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
          <X className="h-4 w-4 text-gray-500" />
        </button>
      </div>

      <div className="grid grid-cols-3 gap-px bg-gray-200 text-center text-sm">
        <div className="bg-white py-3">
          <p className="text-green-600 font-bold text-lg">{result.succeeded}</p>
          <p className="text-gray-500 text-xs">Succeeded</p>
        </div>
        <div className="bg-white py-3">
          <p className="text-red-600 font-bold text-lg">{result.failed}</p>
          <p className="text-gray-500 text-xs">Failed</p>
        </div>
        <div className="bg-white py-3">
          <p className="text-yellow-600 font-bold text-lg">{result.skipped}</p>
          <p className="text-gray-500 text-xs">Skipped</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-2">
        {result.results.map((r) => (
          <div key={r.name} className="flex items-start gap-2.5">
            {r.state === "ok" ? (
              <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
            ) : r.state === "error" ? (
              <XCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
            ) : (
              <Clock className="h-4 w-4 text-yellow-500 mt-0.5 shrink-0" />
            )}
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-800 truncate">{r.name}</p>
              {r.error && (
                <p className="text-xs text-red-500 mt-0.5 truncate">{r.error}</p>
              )}
              <p className="text-xs text-gray-400">{r.duration_seconds}s</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
