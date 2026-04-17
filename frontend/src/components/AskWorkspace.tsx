"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { askCourtVue, getQueryExamples, getQueryMetrics } from "@/lib/api";
import type {
  QueryAskResponse,
  QueryExample,
  QueryMetricMetadata,
  QueryResultRow,
} from "@/lib/types";

type SortDirection = "asc" | "desc";

interface SortState {
  key: string;
  direction: SortDirection;
}

const METRIC_COLUMN_PRIORITY = [
  "pts_pg",
  "reb_pg",
  "ast_pg",
  "ts_pct",
  "off_rating",
  "def_rating",
  "net_rating",
  "pace",
  "wins",
  "losses",
  "pts",
  "reb",
  "ast",
  "min",
  "plus_minus",
];

const FALLBACK_EXAMPLES: QueryExample[] = [
  {
    category: "Player Leaders",
    prompt: "Who leads the NBA in points per game this season?",
    description: "Rank players by a season metric.",
  },
  {
    category: "Team Rankings",
    prompt: "Best teams by net rating in 2025-26",
    description: "Rank teams with official season stats.",
  },
  {
    category: "Recent Form",
    prompt: "How has Shai played recently?",
    description: "Use synced game logs for recent form.",
  },
];

function metricLabel(key: string, metadata?: QueryMetricMetadata) {
  if (metadata) return metadata.label;
  const fallback: Record<string, string> = {
    gp: "GP",
    wins: "W",
    losses: "L",
    pts: "PTS",
    reb: "REB",
    ast: "AST",
    min: "MIN",
    plus_minus: "+/-",
  };
  return fallback[key] ?? key.replace(/_/g, " ").toUpperCase();
}

function formatMetricValue(value: string | number | null | undefined, metadata?: QueryMetricMetadata) {
  if (value == null || value === "") return "-";
  if (typeof value === "string") return value;
  if (metadata?.format === "percent") return `${(value * 100).toFixed(1)}%`;
  if (metadata?.format === "integer") return Math.round(value).toLocaleString();
  if (Number.isInteger(value)) return value.toLocaleString();
  return value.toFixed(1);
}

function sortValue(row: QueryResultRow, key: string): string | number {
  if (key === "rank") return row.rank;
  if (key === "name") return row.name;
  if (key === "value") return row.value ?? Number.NEGATIVE_INFINITY;
  const value = row.metrics[key];
  if (typeof value === "number") return value;
  if (typeof value === "string") return value;
  return Number.NEGATIVE_INFINITY;
}

function sortRows(rows: QueryResultRow[], sort: SortState) {
  return [...rows].sort((a, b) => {
    const aValue = sortValue(a, sort.key);
    const bValue = sortValue(b, sort.key);
    if (typeof aValue === "number" && typeof bValue === "number") {
      return sort.direction === "asc" ? aValue - bValue : bValue - aValue;
    }
    return sort.direction === "asc"
      ? String(aValue).localeCompare(String(bValue))
      : String(bValue).localeCompare(String(aValue));
  });
}

export default function AskWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryParam = searchParams.get("q") ?? "";
  const [draft, setDraft] = useState(queryParam);
  const [examples, setExamples] = useState<QueryExample[]>(FALLBACK_EXAMPLES);
  const [globalMetrics, setGlobalMetrics] = useState<QueryMetricMetadata[]>([]);
  const [response, setResponse] = useState<QueryAskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [sort, setSort] = useState<SortState>({ key: "rank", direction: "asc" });

  useEffect(() => {
    getQueryExamples()
      .then((items) => setExamples(items.length ? items : FALLBACK_EXAMPLES))
      .catch(() => setExamples(FALLBACK_EXAMPLES));
    getQueryMetrics()
      .then(setGlobalMetrics)
      .catch(() => setGlobalMetrics([]));
  }, []);

  useEffect(() => {
    if (!queryParam.trim()) {
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      setIsLoading(true);
      setError(null);
      askCourtVue({ question: queryParam })
        .then((payload) => {
          if (!cancelled) {
            setResponse(payload);
            setSort({ key: "rank", direction: "asc" });
          }
        })
        .catch((err) => {
          if (!cancelled) {
            setResponse(null);
            setError(err instanceof Error ? err.message : "CourtVue Ask could not answer that right now.");
          }
        })
        .finally(() => {
          if (!cancelled) setIsLoading(false);
        });
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [queryParam]);

  const metadataMap = useMemo(() => {
    const map = new Map<string, QueryMetricMetadata>();
    for (const metric of globalMetrics) map.set(metric.key, metric);
    for (const metric of response?.metrics ?? []) map.set(metric.key, metric);
    return map;
  }, [globalMetrics, response?.metrics]);

  const metricColumns = useMemo(() => {
    const keys = new Set<string>();
    for (const row of response?.rows ?? []) {
      Object.keys(row.metrics ?? {}).forEach((key) => keys.add(key));
    }
    return Array.from(keys).sort((a, b) => {
      const aIndex = METRIC_COLUMN_PRIORITY.indexOf(a);
      const bIndex = METRIC_COLUMN_PRIORITY.indexOf(b);
      if (aIndex !== -1 || bIndex !== -1) {
        return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
      }
      return metricLabel(a, metadataMap.get(a)).localeCompare(metricLabel(b, metadataMap.get(b)));
    });
  }, [metadataMap, response?.rows]);

  const sortedRows = useMemo(
    () => sortRows(response?.rows ?? [], sort),
    [response?.rows, sort]
  );

  function submitQuestion(question: string) {
    const trimmed = question.trim();
    if (!trimmed) return;
    setDraft(trimmed);
    router.push(`/ask?q=${encodeURIComponent(trimmed)}`);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitQuestion(draft);
  }

  function toggleSort(key: string) {
    setSort((current) =>
      current.key === key
        ? { key, direction: current.direction === "asc" ? "desc" : "asc" }
        : { key, direction: key === "rank" || key === "name" ? "asc" : "desc" }
    );
  }

  const intentLabel = response?.intent.entity_type
    ? `${response.intent.entity_type} ${response.intent.intent_type.replace(/_/g, " ")}`
    : response?.intent.intent_type.replace(/_/g, " ");

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)] px-5 py-6 shadow-[0_18px_48px_rgba(53,41,33,0.10)] sm:px-7">
        <div className="absolute inset-x-0 top-0 h-1 bg-[linear-gradient(90deg,#21483b,#b4893d,#7f332b)]" />
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div>
            <p className="bip-kicker mb-3">CourtVue Ask</p>
            <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)] sm:text-5xl">
              Ask for the number behind the question.
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-8 text-[var(--muted-strong)]">
              Pull player leaders, team rankings, threshold filters, recent form, and compare links from the data already synced into CourtVue.
            </p>
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-[rgba(255,255,255,0.52)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              Good starting points
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {examples.slice(0, 4).map((example) => (
                <button
                  key={example.prompt}
                  type="button"
                  onClick={() => submitQuestion(example.prompt)}
                  title={example.description}
                  className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-left text-xs font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)]"
                >
                  {example.prompt}
                </button>
              ))}
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-7 flex flex-col gap-3 md:flex-row">
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            className="bip-input min-h-14 flex-1 rounded-lg px-4 text-base"
            placeholder="Try: players with at least 25 ppg and 60 ts%"
            aria-label="Ask CourtVue"
          />
          <button
            type="submit"
            className="rounded-lg bg-[var(--accent)] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isLoading || !draft.trim()}
          >
            {isLoading ? "Asking..." : "Ask"}
          </button>
        </form>
      </section>

      {error ? (
        <div className="rounded-lg border border-[var(--danger)] bg-[rgba(127,51,43,0.08)] p-5 text-sm text-[var(--danger-ink)]">
          {error}
        </div>
      ) : null}

      {!response && !isLoading && !error ? (
        <section className="grid gap-4 md:grid-cols-3">
          {examples.slice(0, 6).map((example) => (
            <button
              key={example.prompt}
              type="button"
              onClick={() => submitQuestion(example.prompt)}
              className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5 text-left transition hover:-translate-y-0.5 hover:border-[var(--accent)] hover:shadow-[0_18px_40px_rgba(33,72,59,0.12)]"
            >
              <p className="bip-kicker">{example.category}</p>
              <p className="mt-3 text-base font-semibold text-[var(--foreground)]">{example.prompt}</p>
              <p className="mt-3 text-sm leading-6 text-[var(--muted)]">{example.description}</p>
            </button>
          ))}
        </section>
      ) : null}

      {response ? (
        <section className="space-y-5">
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[0_16px_42px_rgba(53,41,33,0.08)]">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="bip-kicker mb-2">{intentLabel}</p>
                <h2 className="bip-display text-3xl font-semibold text-[var(--foreground)]">
                  {response.answer.title}
                </h2>
                <p className="mt-3 max-w-3xl text-base leading-7 text-[var(--muted-strong)]">
                  {response.answer.summary}
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <span className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs font-semibold text-[var(--muted-strong)]">
                    {response.intent.season ?? "Season"} - {response.source}
                  </span>
                  {response.intent.filters.map((filter) => (
                    <span
                      key={`${filter.metric_key}-${filter.value}`}
                      className="rounded-lg border border-[var(--accent-soft)] bg-[rgba(33,72,59,0.08)] px-3 py-1.5 text-xs font-semibold text-[var(--accent-strong)]"
                    >
                      {filter.label} {filter.operator === "gte" ? "at least" : "at most"} {filter.formatted_value}
                    </span>
                  ))}
                </div>
              </div>
              <div className="min-w-44 rounded-lg border border-[var(--border)] bg-[rgba(33,72,59,0.06)] p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                  {response.answer.primary_label ?? "Result"}
                </p>
                <p className="mt-2 text-3xl font-semibold text-[var(--foreground)]">
                  {response.answer.primary_value ?? "-"}
                </p>
                {response.answer.href ? (
                  <Link
                    href={response.answer.href}
                    className="bip-link mt-3 inline-flex text-sm font-semibold"
                  >
                    Open workspace
                  </Link>
                ) : null}
              </div>
            </div>

            {response.warnings.length ? (
              <div className="mt-4 rounded-lg border border-[rgba(180,137,61,0.32)] bg-[rgba(180,137,61,0.10)] p-3 text-sm text-[var(--muted-strong)]">
                {response.warnings.join(" ")}
              </div>
            ) : null}
          </div>

          {response.rows.length ? (
            <div className="overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)]">
              <div className="overflow-x-auto">
                <table className="min-w-full border-collapse text-sm">
                  <thead className="bg-[rgba(53,41,33,0.06)] text-left text-xs uppercase tracking-[0.14em] text-[var(--muted)]">
                    <tr>
                      <SortableHeader label="#" sortKey="rank" activeSort={sort} onSort={toggleSort} />
                      <SortableHeader label="Name" sortKey="name" activeSort={sort} onSort={toggleSort} />
                      <SortableHeader
                        label={response.intent.metric_label ?? "Result"}
                        sortKey="value"
                        activeSort={sort}
                        onSort={toggleSort}
                        title={response.metrics.find((metric) => metric.key === response.intent.metric_key)?.description}
                      />
                      {metricColumns.map((key) => (
                        <SortableHeader
                          key={key}
                          label={metricLabel(key, metadataMap.get(key))}
                          sortKey={key}
                          activeSort={sort}
                          onSort={toggleSort}
                          title={metadataMap.get(key)?.description}
                        />
                      ))}
                      <th className="whitespace-nowrap px-4 py-3 font-semibold">Open</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {sortedRows.map((row) => (
                      <tr key={`${row.entity_type}-${row.entity_id ?? row.rank}`} className="hover:bg-[rgba(33,72,59,0.045)]">
                        <td className="whitespace-nowrap px-4 py-3 font-semibold text-[var(--muted)]">{row.rank}</td>
                        <td className="min-w-56 px-4 py-3">
                          <div className="font-semibold text-[var(--foreground)]">{row.name}</div>
                          <div className="text-xs text-[var(--muted)]">
                            {row.subtitle ?? row.team_abbreviation ?? row.abbreviation ?? row.entity_type}
                          </div>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-base font-semibold text-[var(--accent-strong)]">
                          {row.formatted_value ?? formatMetricValue(row.value)}
                        </td>
                        {metricColumns.map((key) => (
                          <td key={key} className="whitespace-nowrap px-4 py-3 text-[var(--foreground)]">
                            {formatMetricValue(row.metrics[key], metadataMap.get(key))}
                          </td>
                        ))}
                        <td className="whitespace-nowrap px-4 py-3">
                          {row.detail_url ? (
                            <Link href={row.detail_url} className="bip-link text-sm font-semibold">
                              Open
                            </Link>
                          ) : (
                            <span className="text-[var(--muted)]">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {response.suggestions.length ? (
            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
              <p className="bip-kicker mb-3">Try next</p>
              <div className="flex flex-wrap gap-2">
                {response.suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => submitQuestion(suggestion)}
                    className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)]"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

function SortableHeader({
  label,
  sortKey,
  activeSort,
  onSort,
  title,
}: {
  label: string;
  sortKey: string;
  activeSort: SortState;
  onSort: (key: string) => void;
  title?: string;
}) {
  const isActive = activeSort.key === sortKey;
  return (
    <th className="whitespace-nowrap px-4 py-3 font-semibold">
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        title={title}
        className="inline-flex items-center gap-1 text-left transition hover:text-[var(--accent-strong)]"
      >
        <span>{label}</span>
        <span className={isActive ? "text-[var(--accent-strong)]" : "text-[var(--muted)]"}>
          {isActive ? (activeSort.direction === "asc" ? "^" : "v") : "sort"}
        </span>
      </button>
    </th>
  );
}
