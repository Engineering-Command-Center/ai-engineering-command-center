export function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 animate-fade-in">
      <div className="h-7 w-7 rounded-full bg-brand-500 flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">
        AI
      </div>
      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex items-center gap-1.5 h-5">
          <span
            className="h-1.5 w-1.5 rounded-full bg-[var(--text-muted)]"
            style={{ animation: "pulse-dot 1.2s ease-in-out infinite", animationDelay: "0ms" }}
          />
          <span
            className="h-1.5 w-1.5 rounded-full bg-[var(--text-muted)]"
            style={{ animation: "pulse-dot 1.2s ease-in-out infinite", animationDelay: "200ms" }}
          />
          <span
            className="h-1.5 w-1.5 rounded-full bg-[var(--text-muted)]"
            style={{ animation: "pulse-dot 1.2s ease-in-out infinite", animationDelay: "400ms" }}
          />
        </div>
      </div>
    </div>
  );
}
