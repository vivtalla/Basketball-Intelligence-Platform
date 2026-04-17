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
    <div className="inline-flex items-baseline gap-2.5">
      <span
        className="bip-display tabular-nums"
        style={{
          fontSize: "clamp(2.5rem, 5vw, 3.25rem)",
          fontWeight: 700,
          lineHeight: 1,
          color: "var(--foreground)",
          fontVariantNumeric: "tabular-nums",
          letterSpacing: "-0.02em",
        }}
      >
        {count.toLocaleString()}
      </span>
      <span
        style={{
          fontSize: 13,
          color: "var(--muted)",
          letterSpacing: "0.04em",
        }}
      >
        {label}
      </span>
    </div>
  );
}
