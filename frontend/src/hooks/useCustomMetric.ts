"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface CustomMetricComponentInput {
  stat_id: string;
  label: string;
  weight: number;
  inverse: boolean;
}

export interface CustomMetricConfig {
  metric_name?: string;
  player_pool: "all" | "position_filter" | "team_filter";
  season: string;
  team_abbreviation?: string;
  position?: string;
  components: CustomMetricComponentInput[];
}

export interface CustomMetricRankingRow {
  rank: number;
  player_name: string;
  team: string;
  composite_score: number;
  component_breakdown: Record<string, number>;
}

export interface CustomMetricNarrative {
  player_name: string;
  narrative: string;
}

export interface CustomMetricAnomaly {
  player_name: string;
  dominant_stat: string;
  contribution_pct: number;
}

export interface CustomMetricResponse {
  metric_label: string;
  metric_interpretation: string;
  player_rankings: CustomMetricRankingRow[];
  top_player_narratives: CustomMetricNarrative[];
  anomalies: CustomMetricAnomaly[];
  validation_warnings: string[];
}

export function useCustomMetric() {
  const [data, setData] = useState<CustomMetricResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  function resetMetric() {
    setData(null);
    setError(null);
  }

  async function runMetric(config: CustomMetricConfig) {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/leaderboards/custom-metric`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail || `API error: ${response.status}`);
      }
      setData(payload as CustomMetricResponse);
      return payload as CustomMetricResponse;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Custom metric request failed.";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }

  return {
    data,
    error,
    isLoading,
    runMetric,
    resetMetric,
  };
}
