"use client";

import { useHealth } from "@/hooks/useHealth";
import { cn } from "@/lib/utils";

export function Header({ title }: { title: string }) {
  const { data } = useHealth();

  return (
    <header className="h-14 border-b border-gray-200 flex items-center justify-between px-6 bg-white">
      <h2 className="text-base font-semibold text-gray-800">{title}</h2>
      <div className="flex items-center gap-2 text-sm">
        <span
          className={cn(
            "h-2 w-2 rounded-full",
            data?.status === "ok" ? "bg-green-500" : "bg-yellow-500"
          )}
        />
        <span className="text-gray-500">
          {data?.status === "ok" ? "All systems operational" : "Degraded"}
        </span>
      </div>
    </header>
  );
}
