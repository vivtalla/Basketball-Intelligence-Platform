"use client";

interface ThreeUnavailableStateProps {
  title: string;
  description: string;
  note?: string;
}

export default function ThreeUnavailableState({
  title,
  description,
  note,
}: ThreeUnavailableStateProps) {
  return (
    <div className="flex h-full min-h-[18rem] flex-col items-center justify-center gap-3 rounded-[1rem] border border-dashed border-[rgba(25,52,42,0.16)] bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.95),rgba(239,231,214,0.72))] px-6 py-8 text-center">
      <div className="rounded-full border border-[rgba(25,52,42,0.12)] bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">
        3D unavailable
      </div>
      <h4 className="text-lg font-semibold text-[var(--foreground)]">{title}</h4>
      <p className="max-w-xl text-sm leading-6 text-[var(--muted-strong)]">{description}</p>
      {note ? <p className="text-xs text-[var(--muted)]">{note}</p> : null}
    </div>
  );
}
