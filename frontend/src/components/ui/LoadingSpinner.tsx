import { cn } from "@/lib/utils";

export function LoadingSpinner({ className }: { className?: string }) {
  return (
    <div
      className={cn("animate-spin rounded-full border-2 border-gray-300 border-t-brand-500 h-6 w-6", className)}
      role="status"
      aria-label="Loading"
    />
  );
}
