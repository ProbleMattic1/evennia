"use client";

import { LocationBanner } from "@/components/location-banner";
import type { RoomAmbient } from "@/lib/ui-api";
import { EMPTY_ROOM_AMBIENT } from "@/lib/ui-api";
import { useMsgStream } from "@/lib/use-msg-stream";

export function VenueLocationBanner({
  roomName,
  ambient,
}: {
  roomName: string;
  ambient?: RoomAmbient | null;
}) {
  const { messages } = useMsgStream();
  return (
    <LocationBanner
      ambient={ambient ?? EMPTY_ROOM_AMBIENT}
      roomName={roomName}
      variant="full"
      messages={messages}
    />
  );
}
