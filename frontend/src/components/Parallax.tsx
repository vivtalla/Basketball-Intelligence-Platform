"use client";

import { useRef, useState, type CSSProperties, type ReactNode } from "react";

interface ParallaxProps {
  children: ReactNode;
  strength?: number;
  className?: string;
  style?: CSSProperties;
}

export default function Parallax({ children, strength = 14, className, style }: ParallaxProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [t, setT] = useState({ x: 0, y: 0 });

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const r = ref.current?.getBoundingClientRect();
    if (!r) return;
    const x = ((e.clientX - r.left) / r.width - 0.5) * strength;
    const y = ((e.clientY - r.top) / r.height - 0.5) * strength;
    setT({ x, y });
  };
  const onLeave = () => setT({ x: 0, y: 0 });

  return (
    <div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      className={className}
      style={{ position: "relative", ...style }}
    >
      <div
        style={{
          transform: `translate(${t.x}px, ${t.y}px)`,
          transition: "transform 220ms cubic-bezier(0.33,1,0.68,1)",
          height: "100%",
          width: "100%",
        }}
      >
        {children}
      </div>
    </div>
  );
}
