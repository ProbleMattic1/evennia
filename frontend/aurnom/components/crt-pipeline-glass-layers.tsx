"use client";

import type { CSSProperties } from "react";

const GLASS_STYLE: CSSProperties = {
  background: [
    "linear-gradient(125deg, rgba(255,255,255,0.09) 0%, transparent 40%, transparent 60%, rgba(255,255,255,0.04) 100%)",
    "linear-gradient(180deg, rgba(255,255,255,0.06) 0%, transparent 8%, transparent 92%, rgba(0,0,0,0.12) 100%)",
  ].join(", "),
  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.12), inset 0 -1px 0 rgba(0,0,0,0.26)",
  mixBlendMode: "soft-light",
  opacity: 0.82,
};

/** Specular “glass” sheet; place above CRT treatments, below text (higher z-index). */
export function CrtGlassSpecularLayer({ zIndex }: { zIndex: number }) {
  return (
    <div
      className="pointer-events-none absolute inset-0 rounded-[inherit]"
      style={{ ...GLASS_STYLE, zIndex }}
      aria-hidden
    />
  );
}
