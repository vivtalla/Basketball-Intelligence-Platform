"use client";

interface Props {
  message?: string;
  onRetry?: () => void;
}

export function ErrorPanel({ message = "Failed to load data", onRetry }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--panel)] p-6 text-center">
      <p className="text-sm text-[var(--muted-strong)]">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="bip-toggle rounded-full px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.1em]"
        >
          Retry
        </button>
      )}
    </div>
  );
}
