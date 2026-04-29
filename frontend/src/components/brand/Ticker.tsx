"use client";

import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";

interface UseCountUpOptions {
  duration?: number;
  decimals?: number;
  start?: number;
}

/**
 * Ease-out cubic count-up to a numeric target, anchored to the lifecycle
 * of the calling component. Returns the current rAF-driven value.
 */
export function useCountUp(target: number, opts: UseCountUpOptions = {}): number {
  const { duration = 1100, start = 0 } = opts;
  const [v, setV] = useState(start);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const t0 = performance.now();
    const from = v;
    function tick(now: number) {
      const t = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setV(from + (target - from) * eased);
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, duration]);

  return v;
}

interface TickerProps {
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  style?: CSSProperties;
  className?: string;
}

/**
 * Animated number — counts up from previous render to `value`.
 * Always tabular-nums. Supports decimals (default 1), prefix/suffix.
 *
 * For integer counts (e.g. "4,892 players tracked") on the home hero,
 * keep using `<StatCounter />` which has built-in label + display
 * styling. `<Ticker />` is the pure numeric primitive — drop into any
 * existing markup.
 */
export default function Ticker({
  value,
  decimals = 1,
  prefix = "",
  suffix = "",
  style,
  className,
}: TickerProps) {
  const v = useCountUp(value, { decimals });
  return (
    <span
      className={className}
      style={{ fontVariantNumeric: "tabular-nums", ...style }}
    >
      {prefix}
      {v.toFixed(decimals)}
      {suffix}
    </span>
  );
}
