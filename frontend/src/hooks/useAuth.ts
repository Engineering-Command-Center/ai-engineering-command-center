"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { User } from "@/types/auth";

export function useAuth() {
  return useQuery<User | null>({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      try {
        // Call the Next.js proxy route (same origin = cookie always sent)
        const res = await fetch("/api/auth/me");
        if (!res.ok) return null;
        return await res.json() as User;
      } catch {
        return null;
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await fetch("/api/auth/logout", { method: "POST" });
    },
    onSuccess: () => {
      qc.setQueryData(["auth", "me"], null);
      window.location.href = "/login";
    },
  });
}
