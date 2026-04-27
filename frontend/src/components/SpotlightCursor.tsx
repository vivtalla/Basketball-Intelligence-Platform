"use client";

import { useEffect, useRef, useState } from "react";

interface SpotlightCursorProps {
  color?: string;
  radius?: number;
}

export default function SpotlightCursor({
  color = "rgba(33,72,59,0.18)",
  radius = 320,
}: SpotlightCursorProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState({ x: -9999, y: -9999 });

  useEffect(() => {
    const parent = ref.current?.parentElement;
    if (!parent) return;
    const onMove = (e: MouseEvent) => {
      const r = parent.getBoundingClientRect();
      setPos({ x: e.clientX - r.left, y: e.clientY - r.top });
    };
    const onLeave = () => setPos({ x: -9999, y: -9999 });
    parent.addEventListener("mousemove", onMove);
    parent.addEventListener("mouseleave", onLeave);
    return () => {
      parent.removeEventListener("mousemove", onMove);
      parent.removeEventListener("mouseleave", onLeave);
    };
  }, []);

  return (
    <div
      ref={ref}
      aria-hidden
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        overflow: "hidden",
        borderRadius: "inherit",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: pos.x - radius,
          top: pos.y - radius,
          width: radius * 2,
          height: radius * 2,
          background: `radial-gradient(circle, ${color} 0%, transparent 60%)`,
          transition: "opacity 260ms",
          opacity: pos.x < 0 ? 0 : 1,
          pointerEvents: "none",
        }}
      />
    </div>
  );
}
