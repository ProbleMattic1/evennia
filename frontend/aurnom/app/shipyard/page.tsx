"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const SHOWROOM_BY_VENUE: Record<string, string> = {
  nanomega_core: "Meridian Civil Shipyard",
  frontier_outpost: "Frontier Meridian Civil Shipyard",
};

function ShipyardRedirectInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const v = searchParams.get("venue")?.trim() || "nanomega_core";
  const room = SHOWROOM_BY_VENUE[v];

  useEffect(() => {
    if (!room) return;
    router.replace(`/shop?room=${encodeURIComponent(room)}`);
  }, [router, room]);

  if (!room) {
    return <p className="p-4 text-sm text-red-600 dark:text-red-400">Unknown shipyard venue: {v}</p>;
  }
  return <p className="p-4 text-sm text-ui-muted">Redirecting…</p>;
}

export default function ShipyardPage() {
  return (
    <Suspense fallback={<p className="p-4 text-sm text-ui-muted">Loading…</p>}>
      <ShipyardRedirectInner />
    </Suspense>
  );
}
