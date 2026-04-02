"use client";

import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

type Props = { children: ReactNode };

/**
 * Decorative shell for the always-visible Missions panel only.
 * Presentation-only; no server / control-surface contract.
 */
export function HitekMissionsChrome({ children }: Props) {
  const reduce = useReducedMotion();
  const corner = "pointer-events-none absolute h-5 w-5";
  return (
    <div className="relative rounded-sm p-[2px]">
      <div
        className="pointer-events-none absolute inset-0 rounded-sm opacity-90"
        style={{
          background:
            "linear-gradient(135deg, rgba(180, 30, 30, 0.12) 0%, transparent 42%, rgba(0, 220, 255, 0.06) 100%)",
          boxShadow:
            "0 0 0 1px rgba(0, 230, 255, 0.25), inset 0 0 24px rgba(180, 20, 20, 0.08), 0 0 20px rgba(0, 200, 255, 0.06)",
        }}
      />
      <div
        className={`${corner} left-0 top-0 border-l-2 border-t-2 border-cyber-cyan/80 shadow-[0_0_8px_rgba(0,230,255,0.25)]`}
      />
      <div
        className={`${corner} right-0 top-0 border-r-2 border-t-2 border-red-500/90 shadow-[0_0_10px_rgba(255,80,80,0.35)]`}
      />
      <div
        className={`${corner} bottom-0 right-0 border-b-2 border-r-2 border-cyber-cyan/80 shadow-[0_0_8px_rgba(0,230,255,0.25)]`}
      />
      <div
        className={`${corner} bottom-0 left-0 border-b-2 border-l-2 border-cyber-cyan/80 shadow-[0_0_8px_rgba(0,230,255,0.25)]`}
      />
      {!reduce ? (
        <motion.div
          className="pointer-events-none absolute inset-0 rounded-sm"
          initial={false}
          animate={{ opacity: [0.55, 0.95, 0.55] }}
          transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
          style={{ boxShadow: "inset 0 0 32px rgba(0, 230, 255, 0.04)" }}
        />
      ) : null}
      <div className="relative z-10">{children}</div>
    </div>
  );
}
