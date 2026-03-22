"use client";

import { useCallback } from "react";
import { useSearchParams } from "next/navigation";

import { ActionGrid } from "@/components/action-grid";
import { ExitGrid } from "@/components/exit-grid";
import { StoryPanel } from "@/components/story-panel";
import { getPlayState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

export default function PlayPage() {
  const searchParams = useSearchParams();
  const room = searchParams.get("room") ?? undefined;
  const loader = useCallback(() => getPlayState(room), [room]);
  const { data, error, loading } = useUiResource(loader);

  if (loading) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 px-6 py-10">
        <p className="text-zinc-600">Loading play state...</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 px-6 py-10">
        <p className="text-red-600">Failed to load play state: {error ?? "Unknown error"}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-10">
      <header>
        <h1 className="text-3xl font-bold text-zinc-950">Play</h1>
        <p className="mt-2 text-zinc-600">Current location: {data.roomName}</p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <StoryPanel title="Story Output" lines={data.storyLines} />
        <div className="flex flex-col gap-6">
          <ExitGrid exits={data.exits} />
          <ActionGrid actions={data.actions} />
        </div>
      </div>
    </main>
  );
}
