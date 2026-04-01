"use client";

import { useEffect, useMemo, useState, useSyncExternalStore } from "react";

import { BANNER_GRAPHIC_REGISTRY } from "@/components/location-banner-graphics";
import type { BillboardItem } from "@/lib/use-billboard-feed";
import { useBillboardFeed } from "@/lib/use-billboard-feed";
import type { MsgStreamEntry, RoomAmbient, RoomAmbientBannerSlide } from "@/lib/ui-api";

const SLIDE_MS = 5500;

function subscribeReducedMotion(cb: () => void) {
  const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
}

function getReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(subscribeReducedMotion, getReducedMotion, () => false);
}

function billboardRowClass(severity: BillboardItem["severity"]): string {
  if (severity === "alert") return "border-red-500/60 bg-red-950/50 text-red-100";
  if (severity === "warn") return "border-amber-500/55 bg-amber-950/40 text-amber-100";
  return "border-cyan-600/40 bg-cyan-950/35 text-cyan-50";
}

type Props = {
  ambient: RoomAmbient;
  roomName: string;
  variant?: "full" | "compact";
  /** When provided, billboard lines are derived from the same stream as the game log. */
  messages?: MsgStreamEntry[];
};

export function LocationBanner({ ambient, roomName, variant = "full", messages }: Props) {
  const reducedMotion = usePrefersReducedMotion();
  const themeId = ambient.themeId || "default";
  const displayTitle = ambient.label?.trim() || roomName;
  const { items: billboardItems, dismiss } = useBillboardFeed(messages ?? [], roomName);

  const slides: RoomAmbientBannerSlide[] = useMemo(() => {
    if (ambient.bannerSlides.length > 0) {
      return ambient.bannerSlides;
    }
    return [
      {
        id: "fallback",
        title: displayTitle,
        body: ambient.tagline,
        graphicKey: null,
      },
    ];
  }, [ambient.bannerSlides, ambient.tagline, displayTitle]);

  const [slideIdx, setSlideIdx] = useState(0);
  const activeIdx = reducedMotion ? 0 : slideIdx % slides.length;

  useEffect(() => {
    if (reducedMotion || slides.length <= 1) return;
    const t = window.setInterval(() => {
      setSlideIdx((i) => (i + 1) % slides.length);
    }, SLIDE_MS);
    return () => window.clearInterval(t);
  }, [reducedMotion, slides.length]);

  const slide = slides[activeIdx] ?? slides[0];
  const graphic =
    (slide.graphicKey && BANNER_GRAPHIC_REGISTRY[slide.graphicKey]) ||
    (themeId === "industrial" || themeId === "promenade"
      ? BANNER_GRAPHIC_REGISTRY[themeId === "industrial" ? "industrial" : "promenade"]
      : null);

  const marqueeText = useMemo(() => {
    const lines = ambient.marqueeLines.filter((l) => l.trim());
    if (lines.length === 0) return "";
    return lines.join("   ·   ");
  }, [ambient.marqueeLines]);

  const compact = variant === "compact";
  const chipLimit = compact ? 2 : 6;

  return (
    <div
      className={`location-banner border-b ${compact ? "px-1.5 py-1" : "px-2 py-2"}`}
      data-room-theme={themeId === "default" ? undefined : themeId}
    >
      {billboardItems.length > 0 ? (
        <div className={`mb-1.5 flex flex-col gap-1 ${compact ? "text-[10px]" : "text-xs"}`}>
          {billboardItems.map((b) => (
            <div
              key={b.id}
              className={`flex items-center gap-2 rounded border px-2 py-1 ${billboardRowClass(b.severity)}`}
              role="status"
            >
              <span className="min-w-0 flex-1 font-semibold leading-snug">{b.headline}</span>
              <button
                type="button"
                className="shrink-0 rounded border border-white/20 px-1.5 py-0.5 text-[10px] uppercase tracking-wide hover:bg-white/10"
                onClick={() => dismiss(b.id)}
              >
                Dismiss
              </button>
            </div>
          ))}
        </div>
      ) : null}

      <div className={`flex gap-2 ${compact ? "items-center" : "items-start"}`}>
        {!compact && graphic ? (
          <div className="text-[var(--room-banner-accent)]" aria-hidden>
            {graphic}
          </div>
        ) : null}
        <div className="min-w-0 flex-1">
          <div
            className={`transition-opacity duration-500 ${compact ? "min-h-0" : "min-h-[2.75rem]"}`}
            key={slide.id}
          >
            {slide.title ? (
              <h2
                className={`font-bold uppercase tracking-widest text-[var(--room-banner-accent)] ${
                  compact ? "text-[10px] leading-tight" : "text-xs"
                }`}
              >
                {slide.title}
              </h2>
            ) : null}
            {slide.body ? (
              <p className={`mt-0.5 text-[var(--room-banner-muted)] ${compact ? "line-clamp-1 text-[10px]" : "text-xs leading-snug"}`}>
                {slide.body}
              </p>
            ) : null}
          </div>
        </div>
        {ambient.chips.length > 0 ? (
          <div className={`flex shrink-0 flex-wrap justify-end gap-1 ${compact ? "max-w-[40%]" : "max-w-[36%]"}`}>
            {ambient.chips.slice(0, chipLimit).map((c) => (
              <span
                key={c.id}
                className={`rounded border border-[var(--room-banner-border)] bg-black/25 px-1.5 py-0.5 font-mono text-[var(--room-banner-accent)] ${
                  compact ? "text-[9px]" : "text-[10px]"
                }`}
              >
                {c.text}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      {marqueeText ? (
        <div className={`mt-1.5 ${compact ? "text-[9px]" : "text-[10px]"}`}>
          {reducedMotion ? (
            <p className="truncate text-[var(--room-banner-muted)]">{marqueeText}</p>
          ) : (
            <div className="location-banner-marquee-wrap">
              <div className="location-banner-marquee-track font-mono text-[var(--room-banner-muted)]">
                <span className="pr-8">{marqueeText}</span>
                <span className="pr-8" aria-hidden>
                  {marqueeText}
                </span>
              </div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
