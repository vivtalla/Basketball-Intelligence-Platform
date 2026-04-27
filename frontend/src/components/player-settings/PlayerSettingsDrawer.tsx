"use client";

import { FormEvent, useState } from "react";
import { createPlayerAnalysisContext, deletePlayerAnalysisContext } from "@/lib/api";
import { usePlayerAnalysisContexts } from "@/hooks/useAnalysisContexts";
import type { AnalysisContext, AnalysisContextFacet, AnalysisContextType } from "@/lib/types";

interface PlayerSettingsDrawerProps {
  playerId: number;
  season: string | null;
}

const CONTEXT_LABELS: Record<AnalysisContextType, string> = {
  injury: "Injury",
  recovery: "Recovery",
  availability_management: "Availability management",
  manual_note: "Manual note",
};

function sourceLabel(context: AnalysisContext) {
  return context.source === "manual" ? "Manual" : "Injury report";
}

function dateRange(context: AnalysisContext) {
  if (context.start_date && context.end_date) return `${context.start_date} to ${context.end_date}`;
  if (context.start_date) return `Since ${context.start_date}`;
  if (context.end_date) return `Through ${context.end_date}`;
  return "Season-level context";
}

export function PlayerSettingsDrawer({ playerId, season }: PlayerSettingsDrawerProps) {
  const { data, mutate, isLoading } = usePlayerAnalysisContexts(playerId, season, true);
  const [contextType, setContextType] = useState<AnalysisContextType>("injury");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  if (!season) return null;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await createPlayerAnalysisContext(playerId, {
        season: season!,
        context_type: contextType,
        start_date: startDate || null,
        end_date: endDate || null,
        severity: contextType === "manual_note" ? null : "medium",
        note: note || null,
        applies_to: ["trend", "team_fit"] as AnalysisContextFacet[],
      });
      setNote("");
      setStartDate("");
      setEndDate("");
      await mutate();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(contextId: number | null) {
    if (contextId == null) return;
    await deletePlayerAnalysisContext(playerId, contextId);
    await mutate();
  }

  const contexts = data?.contexts ?? [];

  return (
    <details className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4">
      <summary className="cursor-pointer list-none text-sm font-semibold text-[var(--foreground)]">
        Player analysis settings
        <span className="ml-2 text-xs font-normal text-[var(--muted)]">
          Injury and availability context for interpretation
        </span>
      </summary>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr,0.9fr]">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
            Active context
          </h3>
          <div className="mt-2 space-y-2">
            {isLoading ? (
              <div className="h-16 animate-pulse rounded-2xl bg-[var(--surface-alt)]" />
            ) : contexts.length === 0 ? (
              <div className="rounded-2xl bg-[var(--surface-alt)] p-3 text-sm text-[var(--muted)]">
                No injury or manual analysis context for this season yet.
              </div>
            ) : (
              contexts.map((context) => (
                <div
                  key={`${context.source}-${context.id ?? context.start_date}-${context.context_type}`}
                  className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-semibold text-[var(--foreground)]">
                        {CONTEXT_LABELS[context.context_type]} · {sourceLabel(context)}
                      </div>
                      <div className="text-xs text-[var(--muted)]">{dateRange(context)}</div>
                    </div>
                    {context.source === "manual" && (
                      <button
                        type="button"
                        onClick={() => handleDelete(context.id)}
                        className="rounded-full border border-[var(--border)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted-strong)]"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                  {context.note && (
                    <p className="mt-2 text-xs leading-5 text-[var(--muted-strong)]">{context.note}</p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="rounded-2xl bg-[var(--surface-alt)] p-4">
          <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
            Add manual context
          </h3>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            These settings affect CourtVue&apos;s interpretation labels, not the underlying stats.
          </p>

          <label className="mt-3 block text-xs font-semibold text-[var(--foreground)]">
            Context type
            <select
              value={contextType}
              onChange={(event) => setContextType(event.target.value as AnalysisContextType)}
              className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm"
            >
              <option value="injury">Injury</option>
              <option value="recovery">Recovery</option>
              <option value="availability_management">Availability management</option>
              <option value="manual_note">Manual note</option>
            </select>
          </label>

          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="block text-xs font-semibold text-[var(--foreground)]">
              Start date
              <input
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
                className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-xs font-semibold text-[var(--foreground)]">
              End date
              <input
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
                className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm"
              />
            </label>
          </div>

          <label className="mt-3 block text-xs font-semibold text-[var(--foreground)]">
            Note
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows={3}
              placeholder="Example: minutes drop followed ankle recovery, not role trust."
              className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm"
            />
          </label>

          <button
            type="submit"
            disabled={saving}
            className="mt-3 rounded-full bg-[var(--accent)] px-4 py-2 text-xs font-bold uppercase tracking-[0.14em] text-white disabled:opacity-60"
          >
            {saving ? "Saving..." : "Add context"}
          </button>
        </form>
      </div>
    </details>
  );
}
