"use client";

import { useState } from "react";
import type { ShotLabSnapshotPayload } from "@/lib/types";
import { useCreateShotLabSnapshot } from "@/hooks/usePlayerStats";

interface ShotSnapshotButtonProps {
  payload: ShotLabSnapshotPayload;
}

export default function ShotSnapshotButton({ payload }: ShotSnapshotButtonProps) {
  const { createSnapshot, isSaving } = useCreateShotLabSnapshot();
  const [message, setMessage] = useState<string | null>(null);

  async function handleSave() {
    const response = await createSnapshot(payload);
    setMessage(`Snapshot ${response.snapshot_id.slice(0, 8)} saved.`);
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(response.share_url);
      setMessage(`Snapshot ${response.snapshot_id.slice(0, 8)} saved. Link copied.`);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        onClick={() => void handleSave()}
        disabled={isSaving}
        className="rounded-full border border-[rgba(25,52,42,0.12)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--foreground)] transition-colors hover:border-[rgba(25,52,42,0.24)] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSaving ? "Saving..." : "Save snapshot"}
      </button>
      {message ? <span className="text-xs text-[var(--muted)]">{message}</span> : null}
    </div>
  );
}
