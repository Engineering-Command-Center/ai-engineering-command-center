import { BrainCircuit } from "lucide-react";

const EXAMPLES = [
  "How does payment retry work?",
  "Where is authentication handled?",
  "How are background jobs scheduled?",
  "What database migrations exist?",
  "How is error handling implemented?",
  "Explain the API rate limiting strategy",
];

interface Props {
  onSelect: (question: string) => void;
}

export function EmptyState({ onSelect }: Props) {
  return (
    <div className="flex flex-col items-center justify-center h-full py-16 px-6 text-center">
      <div className="h-14 w-14 rounded-2xl bg-brand-500 flex items-center justify-center mb-5 shadow-lg shadow-brand-500/25">
        <BrainCircuit className="h-7 w-7 text-white" />
      </div>

      <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">
        Engineering Assistant
      </h1>
      <p className="text-sm text-[var(--text-muted)] mb-8 max-w-sm">
        Ask anything about your indexed codebase. Answers are grounded in your
        actual source code, configs, and docs.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => onSelect(ex)}
            className="text-left text-sm px-4 py-3 rounded-xl border border-[var(--border)]
                       text-[var(--text-secondary)] bg-[var(--bg-secondary)]
                       hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]
                       hover:border-brand-300 dark:hover:border-brand-700
                       transition-all duration-150"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
