"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

interface RevealProps {
  children: ReactNode;
  delay?: number;
  y?: number;
  threshold?: number;
  className?: string;
  style?: CSSProperties;
}

export default function Reveal({
  children,
  delay = 0,
  y = 18,
  threshold = 0.18,
  className,
  style,
}: RevealProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [seen, setSeen] = useState(false);

  useEffect(() => {
    if (!ref.current || seen) return;
    const node = ref.current;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            setSeen(true);
            io.disconnect();
          }
        });
      },
      { threshold },
    );
    io.observe(node);
    return () => io.disconnect();
  }, [seen, threshold]);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: seen ? 1 : 0,
        transform: seen ? "translateY(0)" : `translateY(${y}px)`,
        transition: `opacity 620ms ${delay}ms cubic-bezier(0.33,1,0.68,1), transform 620ms ${delay}ms cubic-bezier(0.33,1,0.68,1)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
