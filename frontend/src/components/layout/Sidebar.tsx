"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  GitPullRequest,
  MessageSquare,
  Database,
  Activity,
  ScanSearch,
  BrainCircuit,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { useLogout } from "@/hooks/useAuth";
import type { User } from "@/types/auth";

const navItems = [
  { href: "/chat", label: "Chat", icon: BrainCircuit },
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/scanner", label: "Repo Scanner", icon: ScanSearch },
  { href: "/repositories", label: "Repositories", icon: GitPullRequest },
  { href: "/knowledge", label: "Knowledge Base", icon: Database },
  { href: "/health", label: "System Health", icon: Activity },
];

interface Props {
  user: User | null;
}

export function Sidebar({ user }: Props) {
  const pathname = usePathname();
  const logout = useLogout();

  return (
    <aside className="w-60 h-screen bg-[var(--bg-secondary)] border-r border-[var(--border)] flex flex-col fixed left-0 top-0 z-30">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-[var(--border)]">
        <Link href="/chat" className="flex items-center gap-2.5 group">
          <div className="h-7 w-7 rounded-lg bg-brand-500 flex items-center justify-center shrink-0">
            <BrainCircuit className="h-4 w-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--text-primary)] leading-none">Eng Command</p>
            <p className="text-[10px] text-[var(--text-muted)] mt-0.5 leading-none">Center</p>
          </div>
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-brand-500 text-white"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User + controls */}
      <div className="px-3 py-3 border-t border-[var(--border)] space-y-2">
        {user && (
          <div className="flex items-center gap-2.5 px-1">
            {user.picture ? (
              <Image
                src={user.picture}
                alt={user.name}
                width={28}
                height={28}
                className="rounded-full shrink-0"
              />
            ) : (
              <div className="h-7 w-7 rounded-full bg-brand-500 flex items-center justify-center shrink-0 text-white text-xs font-bold">
                {user.name.charAt(0).toUpperCase()}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-[var(--text-primary)] truncate">{user.name}</p>
              <p className="text-[10px] text-[var(--text-muted)] truncate">{user.email}</p>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-1">
            <ThemeToggle />
            {user && (
              <button
                onClick={() => logout.mutate()}
                title="Sign out"
                className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
          <span className="text-[11px] text-[var(--text-muted)]">v0.1.0</span>
        </div>
      </div>
    </aside>
  );
}
