"use client";

import type { CSSProperties, ReactNode } from "react";

import { BANNER_GRAPHIC_REGISTRY } from "@/components/location-banner-graphics";
import type { RoomAmbientTakeoverPanel, RoomAmbientVisualTakeover } from "@/lib/ui-api";

export function billboardAssetUrl(imageKey: string): string {
  return `/billboards/${encodeURIComponent(imageKey.trim())}`;
}

/** Maps server token keys to scoped CSS variables used in ``globals.css``. */
export function visualTakeoverTokenStyles(
  tokens: Record<string, string> | null | undefined,
): CSSProperties {
  if (!tokens) {
    return {};
  }
  const out: Record<string, string> = {};
  if (tokens.takeoverAccent) {
    out["--room-takeover-accent"] = tokens.takeoverAccent;
  }
  if (tokens.takeoverGlow) {
    out["--room-takeover-glow"] = tokens.takeoverGlow;
  }
  if (tokens.takeoverVignette) {
    out["--room-takeover-vignette"] = tokens.takeoverVignette;
  }
  return out as CSSProperties;
}

function TakeoverMedia({
  panel,
  className,
  graphicClassName,
}: {
  panel: RoomAmbientTakeoverPanel;
  className?: string;
  graphicClassName?: string;
}): ReactNode {
  const src = panel.imageKey?.trim() ? billboardAssetUrl(panel.imageKey) : null;
  const graphic =
    panel.graphicKey && BANNER_GRAPHIC_REGISTRY[panel.graphicKey]
      ? BANNER_GRAPHIC_REGISTRY[panel.graphicKey]
      : null;
  if (src) {
    const fitCls = panel.fit === "contain" ? "object-contain" : "object-cover";
    return (
      <img
        src={src}
        alt={panel.alt?.trim() || ""}
        className={`${className ?? ""} ${fitCls}`.trim()}
        loading="lazy"
        decoding="async"
      />
    );
  }
  if (graphic) {
    return <div className={graphicClassName}>{graphic}</div>;
  }
  return null;
}

/**
 * Full-width hero strip below the compact location banner (dashboard) or inside play panels.
 */
export function RoomVisualTakeoverTopStrip({
  panel,
  themeId,
}: {
  panel: RoomAmbientTakeoverPanel | null | undefined;
  themeId: string;
}) {
  if (!panel || (!panel.imageKey?.trim() && !panel.graphicKey)) {
    return null;
  }
  const minH = Math.max(48, Math.min(panel.minHeightPx ?? 140, 480));
  return (
    <div
      className="room-visual-takeover-top relative isolate w-full shrink-0 overflow-hidden border-b border-[var(--room-takeover-border,rgba(34,211,238,0.35))] bg-black/40 shadow-[var(--room-takeover-glow,none)]"
      data-room-theme={themeId === "default" ? undefined : themeId}
      style={{ minHeight: minH }}
    >
      <TakeoverMedia
        panel={panel}
        className="absolute inset-0 size-full"
        graphicClassName="absolute inset-0 flex items-center justify-center text-[var(--room-takeover-accent,var(--accent-cyan))] opacity-90 [&_svg]:size-24 md:[&_svg]:size-32"
      />
      {panel.overlayGradient ? (
        <div
          className="pointer-events-none absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/55 to-transparent opacity-[0.72]"
          aria-hidden
        />
      ) : null}
    </div>
  );
}

/**
 * Vertical rail for md+ dashboard layout; hidden on small viewports.
 */
export function RoomVisualTakeoverSidebarRail({
  panel,
  themeId,
}: {
  panel: RoomAmbientTakeoverPanel | null | undefined;
  themeId: string;
}) {
  if (!panel || (!panel.imageKey?.trim() && !panel.graphicKey)) {
    return null;
  }
  const minH = panel.minHeightPx != null ? Math.max(120, Math.min(panel.minHeightPx, 900)) : 320;
  const pos = panel.position === "right" ? "right" : "left";
  const borderCls =
    pos === "right"
      ? "md:border-l md:border-r-0 border-cyan-900/30"
      : "md:border-r border-cyan-900/30";
  return (
    <aside
      className={`room-visual-takeover-rail hidden min-h-0 w-full min-w-0 bg-black/30 md:flex md:max-w-[11rem] md:flex-col ${borderCls}`}
      data-room-theme={themeId === "default" ? undefined : themeId}
      data-takeover-rail-position={pos}
      aria-label={panel.alt?.trim() || "Venue atmosphere"}
    >
      <div
        className="relative min-h-0 flex-1 overflow-hidden md:sticky md:top-0 md:min-h-[min(100svh,52rem)]"
        style={{ minHeight: minH }}
      >
        <TakeoverMedia
          panel={panel}
          className="absolute inset-0 size-full md:min-h-full"
          graphicClassName="absolute inset-0 flex items-center justify-center text-[var(--room-takeover-accent,var(--accent-cyan))] opacity-90 [&_svg]:h-40 [&_svg]:w-auto"
        />
        {panel.overlayGradient ? (
          <div
            className="pointer-events-none absolute inset-0 bg-gradient-to-r from-zinc-950/80 via-transparent to-zinc-950/40 opacity-70"
            aria-hidden
          />
        ) : null}
      </div>
    </aside>
  );
}

export function takeoverPanelHasMedia(p: RoomAmbientTakeoverPanel | null | undefined): boolean {
  if (!p) {
    return false;
  }
  if (p.imageKey?.trim()) {
    return true;
  }
  const gk = p.graphicKey;
  return Boolean(gk && Object.prototype.hasOwnProperty.call(BANNER_GRAPHIC_REGISTRY, gk));
}

export function hasVisualTakeoverContent(vt: RoomAmbientVisualTakeover | null | undefined): boolean {
  if (!vt) {
    return false;
  }
  return takeoverPanelHasMedia(vt.top) || takeoverPanelHasMedia(vt.sidebar);
}
