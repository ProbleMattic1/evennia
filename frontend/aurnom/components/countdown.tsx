"use client";

import { useCountdown } from "@/lib/use-countdown";

export function Countdown({
  targetIso,
  prefix = "Next in:",
  className,
  onExpired,
}: {
  targetIso: string | null;
  prefix?: string;
  className?: string;
  onExpired?: () => void;
}) {
  const label = useCountdown(targetIso, onExpired);
  if (!label) return null;
  return (
    <span className={className}>
      {prefix ? <>{prefix} </> : null}
      <span className="font-mono tabular-nums">{label}</span>
    </span>
  );
}
