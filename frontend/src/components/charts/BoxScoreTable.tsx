"use client";

import { useMemo, useState } from "react";

export interface BoxScoreRow {
  id?: string | number;
  player: string;
  /** Optional opponent label rendered as a sub-line under the player name. */
  opp?: string;
  /** Game-result string like "W 119-102" — colored green/red. */
  result?: string;
  [key: string]: unknown;
}

export interface BoxScoreColumn {
  key: string;
  label: string;
  numeric?: boolean;
  bold?: boolean;
  /** Hex/CSS-var override for this column's text color. */
  color?: string;
  /** Custom formatter — e.g. (v) => `${(v * 100).toFixed(1)}%`. */
  format?: (value: unknown) => string;
}

interface BoxScoreTableProps {
  rows: BoxScoreRow[];
  columns: BoxScoreColumn[];
  /** Initial sort key. Defaults to the first numeric column. */
  defaultSort?: string;
}

/**
 * BoxScoreTable — sortable NBA-style box score. Mono-cap header,
 * tabular numerals, dashed row dividers, hover row tint. Click a
 * column header to toggle desc/asc. Player column shows an optional
 * opponent + result sub-line.
 */
export default function BoxScoreTable({
  rows,
  columns,
  defaultSort,
}: BoxScoreTableProps) {
  const initialKey =
    defaultSort ??
    columns.find((c) => c.numeric)?.key ??
    columns[1]?.key ??
    columns[0]?.key;
  const [sortBy, setSortBy] = useState<{ key: string; dir: "asc" | "desc" }>(
    () => ({ key: initialKey, dir: "desc" }),
  );

  const sorted = useMemo(() => {
    const arr = [...rows];
    arr.sort((a, b) => {
      const av = a[sortBy.key];
      const bv = b[sortBy.key];
      if (typeof av === "number" && typeof bv === "number") {
        return sortBy.dir === "desc" ? bv - av : av - bv;
      }
      const sa = String(av ?? "");
      const sb = String(bv ?? "");
      return sortBy.dir === "desc" ? sb.localeCompare(sa) : sa.localeCompare(sb);
    });
    return arr;
  }, [rows, sortBy]);

  const grid = `40px 1.4fr ${columns.slice(1).map(() => "70px").join(" ")}`;

  return (
    <div
      className="overflow-hidden rounded-2xl border border-[var(--border)]"
      style={{ background: "rgba(255,249,241,0.86)", backdropFilter: "blur(14px)" }}
    >
      <div
        className="grid items-center gap-2.5 px-5 py-3 text-[10.5px] font-bold uppercase tracking-[0.10em] text-[var(--muted)]"
        style={{
          gridTemplateColumns: grid,
          background: "#f2e8d4",
          fontFamily: "var(--font-geist-mono)",
        }}
      >
        <div>#</div>
        {columns.map((c) => {
          const active = sortBy.key === c.key;
          return (
            <button
              key={c.key}
              onClick={() =>
                setSortBy((s) => ({
                  key: c.key,
                  dir: s.key === c.key && s.dir === "desc" ? "asc" : "desc",
                }))
              }
              className="flex items-center gap-1 text-inherit"
              style={{
                background: "transparent",
                border: 0,
                padding: 0,
                fontFamily: "inherit",
                fontSize: "inherit",
                color: active ? "var(--accent)" : "inherit",
                letterSpacing: "inherit",
                cursor: "pointer",
                fontWeight: "inherit",
                textTransform: "inherit",
                justifyContent: c.numeric ? "flex-end" : "flex-start",
              }}
            >
              {c.label}
              {active && (
                <span style={{ fontSize: 8 }}>{sortBy.dir === "desc" ? "▼" : "▲"}</span>
              )}
            </button>
          );
        })}
      </div>
      {sorted.map((r, i) => {
        const win = r.result?.startsWith("W");
        return (
          <div
            key={r.id ?? i}
            className="grid items-center gap-2.5 px-5 py-3 transition-colors hover:bg-[rgba(33,72,59,0.045)]"
            style={{
              gridTemplateColumns: grid,
              borderTop: i === 0 ? "none" : "1px dashed rgba(53,41,33,0.12)",
            }}
          >
            <div
              className="text-[11px] font-bold text-[var(--muted)]"
              style={{ fontFamily: "var(--font-geist-mono)" }}
            >
              {String(i + 1).padStart(2, "0")}
            </div>
            {columns.map((c, ci) => {
              const val = r[c.key];
              if (ci === 0) {
                return (
                  <div key={c.key} className="flex flex-col gap-0.5">
                    <div
                      className="text-[13.5px] font-medium"
                      style={{ fontFamily: "var(--font-display)" }}
                    >
                      {String(val ?? "")}
                    </div>
                    {r.opp && (
                      <div
                        className="flex items-center gap-1.5 text-[10px] text-[var(--muted)]"
                        style={{
                          fontFamily: "var(--font-geist-mono)",
                          letterSpacing: "0.04em",
                        }}
                      >
                        <span>{r.opp}</span>
                        {r.result && (
                          <span
                            className="font-bold"
                            style={{
                              color: win ? "var(--success-ink)" : "var(--danger-ink)",
                            }}
                          >
                            {r.result}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              }
              const formatted = c.format ? c.format(val) : (val as string | number | null | undefined) ?? "—";
              return (
                <div
                  key={c.key}
                  className="tabular-nums"
                  style={{
                    textAlign: c.numeric ? "right" : "left",
                    fontVariantNumeric: "tabular-nums",
                    fontSize: 13,
                    fontWeight: c.bold ? 600 : 400,
                    color: c.color || "var(--foreground)",
                    fontFamily: "var(--font-geist-sans)",
                  }}
                >
                  {String(formatted)}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
