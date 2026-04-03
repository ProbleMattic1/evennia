"use client";

import { useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

/**
 * CRT horizontal scanlines (::before) and optional moving green sweep (::after) from globals.css.
 * Children are lifted above the pseudo-elements with z-index.
 */
export function PipelineMatrixOverlay({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduceMotion = useReducedMotion();
  const frameCls = [
    "pipeline-matrix-frame",
    "rounded",
    "px-1.5",
    "py-1",
    reduceMotion ? "" : "pipeline-matrix-frame--motion",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={frameCls}>
      <div className="relative z-[2]">{children}</div>
    </div>
  );
}
