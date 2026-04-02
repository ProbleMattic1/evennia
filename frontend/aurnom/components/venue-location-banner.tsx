"use client";

import { LocationBanner } from "@/components/location-banner";
import type { RoomAmbient } from "@/lib/ui-api";
import { EMPTY_ROOM_AMBIENT } from "@/lib/ui-api";
import { useMsgStream } from "@/lib/use-msg-stream";

export function VenueLocationBanner({
  roomName,
  ambient,
  embedded,
  extraBottomPx,
}: {
  roomName: string;
  ambient?: RoomAmbient | null;
  /** Set when banner sits above story text in a single venue panel. */
  embedded?: boolean;
  /** Ignored when `embedded`; default 120 for standalone venue banner. */
  extraBottomPx?: number;
}) {
  const { messages } = useMsgStream();
  const bottom =
    embedded ? undefined : extraBottomPx !== undefined ? extraBottomPx : 120;
  return (
    <LocationBanner
      ambient={ambient ?? EMPTY_ROOM_AMBIENT}
      roomName={roomName}
      variant="full"
      messages={messages}
      extraBottomPx={bottom}
      embedded={embedded}
    />
  );
}
