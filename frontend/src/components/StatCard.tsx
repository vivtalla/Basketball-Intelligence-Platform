interface StatCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
}

export default function StatCard({ label, value, subtitle }: StatCardProps) {
  return (
    <div className="bip-panel rounded-xl p-4 text-center">
      <p className="bip-kicker mb-1 text-[10px]">
        {label}
      </p>
      <p className="text-2xl font-bold text-[var(--foreground)]">{value}</p>
      {subtitle && (
        <p className="mt-1 text-xs text-[var(--muted)]">{subtitle}</p>
      )}
    </div>
  );
}
