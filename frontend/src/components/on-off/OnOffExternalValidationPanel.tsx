"use client";

import type { ExternalValidation } from "@/lib/types";

interface Props {
  validation: ExternalValidation | null;
  onOffNet: number | null;
}

function Chip({ label, value }: { label: string; value: number | null }) {
  const display = value != null ? `${value >= 0 ? "+" : ""}${value.toFixed(1)}` : "—";
  const color = value == null ? "text-gray-400 dark:text-gray-500" : value >= 0 ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400";
  return (
    <div className="flex flex-col items-center rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 py-2 text-center">
      <span className="text-[10px] uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</span>
      <span className={`text-base font-semibold tabular-nums ${color}`}>{display}</span>
    </div>
  );
}

export default function OnOffExternalValidationPanel({ validation, onOffNet }: Props) {
  if (!validation) return null;
  const { rapm, epm, pipm, agreement_note } = validation;
  if (rapm == null && epm == null && pipm == null) return null;

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Chip label="RAPM" value={rapm} />
        <Chip label="EPM" value={epm} />
        <Chip label="PIPM" value={pipm} />
        {onOffNet != null && (
          <Chip label="On/Off Net" value={onOffNet} />
        )}
      </div>
      {agreement_note && (
        <p className="text-[10px] text-gray-500 dark:text-gray-400">{agreement_note}</p>
      )}
      <p className="text-[10px] text-gray-400 dark:text-gray-500 italic">
        External metrics from public datasets. Not platform-original. Always interpret alongside sample size.
      </p>
    </div>
  );
}
