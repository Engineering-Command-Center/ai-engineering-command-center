"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { useAuth } from "@/hooks/useAuth";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

const FULL_SCREEN_ROUTES = new Set(["/chat"]);
const PUBLIC_ROUTES = new Set(["/login"]);

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: user, isLoading } = useAuth();

  const isPublic = PUBLIC_ROUTES.has(pathname);
  const isFullScreen = FULL_SCREEN_ROUTES.has(pathname);

  useEffect(() => {
    if (!isLoading && !user && !isPublic) {
      router.replace("/login");
    }
  }, [isLoading, user, isPublic, router]);

  // Show spinner while checking auth on protected routes
  if (!isPublic && isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-primary)]">
        <LoadingSpinner />
      </div>
    );
  }

  // Not authed on a protected route — blank while redirect fires
  if (!isPublic && !user) return null;

  if (isFullScreen) {
    return (
      <div className="h-screen w-screen overflow-hidden bg-[var(--bg-primary)]">
        {children}
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-[var(--bg-secondary)]">
      <Sidebar user={user ?? null} />
      <main className="ml-60 flex-1 min-h-screen bg-[var(--bg-secondary)]">{children}</main>
    </div>
  );
}
