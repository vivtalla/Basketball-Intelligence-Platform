"use client";

import { useEffect, useRef, useState } from "react";

interface StatCounterProps {
  target: number;
  label: string;
  duration?: number;
}

export default function StatCounter({ target, label, duration = 1800 }: StatCounterProps) {
  const [count, setCount] = useState(0);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const start = performance.now();
    function step(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(eased * target));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(step);
      }
    }
    rafRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration]);

  return (
    <div className="inline-flex flex-col items-center gap-1">
      <span className="bip-display text-5xl font-bold text-[var(--accent)] tabular-nums sm:text-6xl">
        {count.toLocaleString()}+
      </span>
      <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">
        {label}
      </span>
    </div>
  );
}
