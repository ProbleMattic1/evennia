"use client";

import { CrtGlassSpecularLayer } from "@/components/crt-pipeline-glass-layers";
import { motion, useReducedMotion } from "motion/react";
import { useId, type ReactNode } from "react";

type Props = { children: ReactNode; compact?: boolean };

/**
 * Decorative frame for the game log viewport (vintage CRT glass, white + neon green accents).
 */
export function HitekGameLogChrome({ children, compact }: Props) {
  const reduce = useReducedMotion();
  const rawId = useId();
  const noiseFilterId = `crt-noise-${rawId.replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const pad = compact ? "p-[2px]" : "p-1";
  const corner = compact
    ? "pointer-events-none absolute h-4 w-4"
    : "pointer-events-none absolute h-5 w-5";
  const eyePos = compact ? "right-1.5 top-1.5" : "right-2 top-2";
  const eyeSize = compact ? "h-2 w-2" : "h-2.5 w-2.5";

  return (
    <div className={`relative rounded-sm ${pad}`}>
      {/* Outer rim: soft white line + neon green bloom (no warm/red tones) */}
      <div
        className="pointer-events-none absolute inset-0 rounded-sm"
        style={{
          boxShadow: [
            "0 0 0 2px rgba(200, 255, 220, 0.28)",
            "0 0 0 1px rgba(255, 255, 255, 0.12) inset",
            "0 0 36px rgba(57, 255, 120, 0.15)",
            "0 0 56px rgba(180, 255, 200, 0.065)",
            "inset 0 0 48px rgba(0, 0, 0, 0.82)",
            "inset 0 0 72px rgba(0, 35, 22, 0.4)",
          ].join(", "),
        }}
      />

      <div
        className="pointer-events-none absolute left-[4%] right-[14%] top-0 z-[2] h-[3px] rounded-sm"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.2) 22%, rgba(180, 255, 200, 0.95) 48%, rgba(180, 255, 200, 0.95) 52%, rgba(255, 255, 255, 0.2) 78%, transparent 100%)",
          boxShadow:
            "0 0 10px rgba(120, 255, 160, 0.28), 0 0 22px rgba(57, 255, 120, 0.11), 0 1px 0 rgba(255, 255, 255, 0.12)",
        }}
      />

      <div
        className={`${corner} left-0 top-0 border-l-2 border-t-2 border-emerald-300/70 shadow-[0_0_10px_rgba(110,255,160,0.22)]`}
      />
      <div
        className={`${corner} right-0 top-0 border-r-2 border-t-2 border-emerald-400/85 shadow-[0_0_10px_rgba(74,255,140,0.19)]`}
      />
      <div
        className={`${corner} bottom-0 right-0 border-b-2 border-r-2 border-emerald-300/75 shadow-[0_0_9px_rgba(110,255,160,0.18)]`}
      />
      <div
        className={`${corner} bottom-0 left-0 border-b-2 border-l-2 border-white/25 shadow-[0_0_8px_rgba(255,255,255,0.08)]`}
      />

      <div
        className="pointer-events-none absolute bottom-2 left-0 top-8 z-[2] w-0.5 rounded-full bg-gradient-to-b from-emerald-300/85 via-emerald-400/30 to-transparent opacity-75 shadow-[0_0_9px_rgba(100,255,150,0.19)]"
        aria-hidden
      />

      <div className={`pointer-events-none absolute z-[6] ${eyePos}`}>
        <motion.div
          className={`${eyeSize} rounded-full border border-white/40 bg-emerald-400`}
          style={{
            boxShadow:
              "0 0 9px 2px rgba(120, 255, 180, 0.32), 0 0 18px rgba(57, 255, 120, 0.15), inset 0 0 4px rgba(255, 255, 255, 0.6)",
          }}
          animate={
            reduce
              ? undefined
              : { opacity: [0.85, 1, 0.85], scale: [1, 1.14, 1] }
          }
          transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>

      {/* CRT face: clip + stacked glass effects (solid base so log children can stay transparent and show layers) */}
      <div className="relative z-10 min-h-0 overflow-hidden rounded-[3px] bg-zinc-950">
        {/* z-0: green sweep (::after). z-1+: must sit above this or the full-bleed layers hide it. */}
        <div
          className={`pipeline-matrix-sweep-host pointer-events-none absolute inset-0 z-0 rounded-[3px] ${reduce ? "" : "pipeline-matrix-fill--motion"}`}
          aria-hidden
        />

        {/* Dark horizontal bands — CSS keyframes (see globals .crt-log-dark-scanlines) */}
        <div className="pointer-events-none absolute inset-0 z-[1] overflow-hidden rounded-[3px]">
          <div className="crt-log-dark-scanlines" aria-hidden />
        </div>

        <div className="pointer-events-none absolute inset-0 z-[2] overflow-hidden rounded-[3px]">
          {!reduce ? (
            <motion.div
              className="absolute inset-0 opacity-[0.16]"
              style={{
                backgroundImage:
                  "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(120, 255, 170, 0.72) 2px, rgba(120, 255, 170, 0.72) 3px)",
                backgroundSize: "100% 3px",
              }}
              animate={{ backgroundPosition: ["0px 0px", "0px 3px"] }}
              transition={{ duration: 12, repeat: Infinity, ease: "linear" }}
            />
          ) : (
            <div
              className="absolute inset-0 opacity-[0.11]"
              style={{
                backgroundImage:
                  "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(120, 255, 170, 0.58) 2px, rgba(120, 255, 170, 0.58) 3px)",
              }}
            />
          )}
        </div>

        {/* Tube curvature + edge falloff */}
        <div
          className="pointer-events-none absolute inset-0 z-[3]"
          style={{
            background: [
              "radial-gradient(ellipse 96% 88% at 50% 48%, transparent 55%, rgba(0, 0, 0, 0.5) 100%)",
              "linear-gradient(180deg, rgba(0, 0, 0, 0.22) 0%, transparent 12%, transparent 88%, rgba(0, 0, 0, 0.28) 100%)",
              "linear-gradient(90deg, rgba(0, 0, 0, 0.12) 0%, transparent 6%, transparent 94%, rgba(0, 0, 0, 0.12) 100%)",
            ].join(", "),
          }}
        />

        {/* P1-style phosphor cast */}
        <div
          className="pointer-events-none absolute inset-0 z-[4] mix-blend-screen"
          style={{
            background: "radial-gradient(ellipse 85% 70% at 50% 45%, rgba(80, 255, 120, 0.11) 0%, transparent 65%)",
            opacity: 0.78,
          }}
        />

        {/* Film grain */}
        <svg
          className="pointer-events-none absolute inset-0 z-[5] h-full w-full opacity-[0.045]"
          aria-hidden
        >
          <defs>
            <filter id={noiseFilterId} x="-20%" y="-20%" width="140%" height="140%">
              <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="4" stitchTiles="stitch" result="n" />
              <feColorMatrix in="n" type="saturate" values="0" result="g" />
            </filter>
          </defs>
          <rect width="100%" height="100%" filter={`url(#${noiseFilterId})`} />
        </svg>

        {/* Occasional CRT brightness waver */}
        {!reduce ? (
          <motion.div
            className="pointer-events-none absolute inset-0 z-[6] rounded-[2px] bg-black"
            initial={false}
            animate={{ opacity: [0, 0.055, 0.015, 0.085, 0, 0.03, 0] }}
            transition={{ duration: 6.5, repeat: Infinity, ease: "easeInOut" }}
          />
        ) : null}

        <CrtGlassSpecularLayer zIndex={7} />

        <div className="relative z-[8] min-h-0 [filter:saturate(1.08)_contrast(1.04)]">{children}</div>
      </div>
    </div>
  );
}
