"use client";

import { EconomyStatCard } from "@/components/economy-stat-card";

function formatCredits(n: number) {
  const v = Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0;
  return `${v.toLocaleString("en-US")} cr`;
}

function formatBoundaryShort(iso: string | undefined) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString(undefined, {
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function slotHint(periodSec: number | undefined) {
  if (!periodSec || periodSec <= 0) return "previous UTC mining delivery slot";
  const m = Math.round(periodSec / 60);
  if (m >= 60 && m % 60 === 0) {
    return `previous ${m / 60}h UTC mining slot`;
  }
  return `previous ${m}m UTC mining slot`;
}

const HINT_PREFIX =
  "Treasury → players for plant ore intake and refined pickup. “Last slot” = credits paid in the ";

export function EconomyMinerPayoutHero({
  lastCycleCr,
  totalCr,
  miningNextCycleAt,
  miningDeliveryPeriodSeconds,
}: {
  lastCycleCr: number | undefined;
  totalCr: number | undefined;
  miningNextCycleAt?: string;
  miningDeliveryPeriodSeconds?: number;
}) {
  const last = lastCycleCr ?? 0;
  const total = totalCr ?? 0;
  const nextShort = formatBoundaryShort(miningNextCycleAt);

  return (
    <EconomyStatCard
      title="Miner payouts"
      hintTitle={`${HINT_PREFIX}${slotHint(miningDeliveryPeriodSeconds)}; “Total” = all-time.`}
      headerRight={
        nextShort ? (
          <span className="text-[9px] tabular-nums text-ui-soft" title="Current slot ends">
            ends {nextShort}
          </span>
        ) : null
      }
    >
      <div className="grid grid-cols-2 gap-x-3 divide-x divide-cyan-900/35">
        <div className="min-w-0 pr-3">
          <p className="text-[8px] uppercase tracking-wide text-ui-soft">Last slot</p>
          <p className="mt-0.5 truncate text-sm font-semibold tabular-nums text-cyan-400">{formatCredits(last)}</p>
        </div>
        <div className="min-w-0 pl-3">
          <p className="text-[8px] uppercase tracking-wide text-ui-soft">Total</p>
          <p className="mt-0.5 truncate text-sm font-semibold tabular-nums text-cyan-400">{formatCredits(total)}</p>
        </div>
      </div>
    </EconomyStatCard>
  );
}
