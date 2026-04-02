"use client";

import { useEffect, useState, type ReactNode } from "react";

import { StoryPanel } from "@/components/story-panel";
import { VenueLocationBanner } from "@/components/venue-location-banner";
import { useMissionsChromeHeight } from "@/lib/missions-chrome-height-context";
import type { RoomAmbient, StoryLine } from "@/lib/ui-api";

const MD_MIN_WIDTH = 768;
/** Tightens sync to the visible missions chrome; measured block is slightly taller than the cyan frame. */
const MISSIONS_CHROME_HEIGHT_TRIM_PX = 40;

/**
 * Single cyan-bordered block: room billboard on top, story output below.
 * On md+ viewports, `min-height` tracks the Missions/Quests chrome height (left column).
 */
export function VenueBillboardStoryFrame({
  panelTitle,
  roomName,
  ambient,
  storyLines,
  storySubheading = "Story output",
}: {
  panelTitle: ReactNode;
  roomName: string;
  ambient: RoomAmbient;
  storyLines: StoryLine[];
  storySubheading?: string;
}) {
  const missionsChromeH = useMissionsChromeHeight();
  const [isMd, setIsMd] = useState(
    () => typeof window !== "undefined" && window.matchMedia(`(min-width: ${MD_MIN_WIDTH}px)`).matches,
  );

  useEffect(() => {
    const mq = window.matchMedia(`(min-width: ${MD_MIN_WIDTH}px)`);
    const apply = () => setIsMd(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  const minH =
    isMd && missionsChromeH != null && missionsChromeH > 0
      ? Math.max(0, missionsChromeH - MISSIONS_CHROME_HEIGHT_TRIM_PX)
      : undefined;

  return (
    <section
      className="mb-1 flex min-h-0 min-w-0 flex-col"
      style={minH != null && minH > 0 ? { minHeight: minH } : undefined}
    >
      <div className="flex min-w-0 shrink-0 items-center gap-2 bg-cyan-900/30 px-1.5 py-0.5 text-xs font-bold uppercase tracking-widest text-cyber-cyan">
        {panelTitle}
      </div>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col border border-cyan-900/40 bg-zinc-950/80">
        <div className="min-w-0 shrink-0">
          <VenueLocationBanner roomName={roomName} ambient={ambient} embedded />
        </div>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col border-t border-cyan-900/40 p-1.5">
          <div className="mb-0.5 shrink-0 text-xs uppercase tracking-wide text-ui-muted">{storySubheading}</div>
          <StoryPanel lines={storyLines} compact flexFill />
        </div>
      </div>
    </section>
  );
}
