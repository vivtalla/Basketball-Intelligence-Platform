export default function Loading() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-48 rounded-2xl bg-[var(--surface-alt)]" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="h-72 rounded-2xl bg-[var(--surface-alt)]" />
        <div className="h-72 rounded-2xl bg-[var(--surface-alt)] lg:col-span-2" />
      </div>
      <div className="h-96 rounded-2xl bg-[var(--surface-alt)]" />
    </div>
  );
}
