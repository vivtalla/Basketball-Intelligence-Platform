import { CustomMetricBuilder } from "@/components/CustomMetricBuilder";

export default function MetricsPage() {
  return (
    <div className="space-y-8">
      <div className="max-w-4xl">
        <p className="bip-kicker mb-3">Analyst Workflow</p>
        <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)] sm:text-5xl">
          Metrics
        </h1>
        <p className="mt-4 text-base leading-8 text-[var(--muted-strong)]">
          Build composite rankings around the traits you actually care about, reuse presets, and keep the scoring math transparent.
        </p>
      </div>

      <CustomMetricBuilder />
    </div>
  );
}
