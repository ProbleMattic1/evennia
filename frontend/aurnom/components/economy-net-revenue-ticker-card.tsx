"use client";

import { useReducedMotion } from "motion/react";

import type { ControlSurfaceState } from "@/lib/control-surface-api";
import {
  deliverySlotProgress,
  miningCycleProgress,
  miningPeriodSeconds,
} from "@/lib/economy-dashboard-derive";
import { EconomyStatCard } from "@/components/economy-stat-card";
import { useServerAnchoredTimeMs } from "@/lib/use-server-anchored-time";

const HINT =
  "Live client estimate: plant margin accruing this UTC mining slot. " +
  "Equals (estimated slot gross × processing fee rate), stepped by slot progress — same gross basis as mining accrual on the control surface. " +
  "Not wallet credits; settlements and hazards can differ. " +
  "End-of-slot projection and fee rate are context below the main readout.";

function formatPositiveCr(n: number) {
  return `+${Math.max(0, Math.floor(n)).toLocaleString("en-US")} cr`;
}

function formatOutflowCr(n: number) {
  return `−${Math.max(0, Math.floor(n)).toLocaleString("en-US")} cr`;
}

function formatRate(crPerSec: number, sign: "+" | "−") {
  if (!Number.isFinite(crPerSec) || crPerSec <= 0) return `${sign}0 cr/s`;
  if (crPerSec >= 1) return `${sign}${crPerSec.toFixed(2)} cr/s`;
  return `${sign}${(crPerSec * 100).toFixed(1)} ¢/s`;
}

export function EconomyNetRevenueTickerCard({ data }: { data: ControlSurfaceState }) {
  const reduceMotion = useReducedMotion();
  const nowMs = useServerAnchoredTimeMs(data.serverTimeIso);
  const period = miningPeriodSeconds(data);

  const cap = data.miningAccrualValuePerCycle ?? data.productionEstimatedValuePerCycle ?? 0;
  const feeRate = data.processing?.processingFeeRate ?? 0;
  const minerRate = 1 - feeRate;

  const slotProgress = data.miningSlotStartIso
    ? deliverySlotProgress(nowMs, data.miningSlotStartIso, period)
    : miningCycleProgress(nowMs, data.miningNextCycleAt, period);

  const maxMarginThisSlot = Math.floor(cap * feeRate);
  const maxMinerThisSlot = Math.floor(cap * minerRate);
  const liveMarginCr = Math.min(maxMarginThisSlot, Math.floor(cap * feeRate * slotProgress));

  const feesCrPerSec = period > 0 ? (cap * feeRate) / period : 0;
  const costCrPerSec = period > 0 ? (cap * minerRate) / period : 0;

  const pct = Math.round(slotProgress * 100);
  const projectedEndFees = maxMarginThisSlot;
  const projectedEndCost = maxMinerThisSlot;

  return (
    <EconomyStatCard
      title="Plant margin accrual (this slot)"
      hintTitle={HINT}
      headerRight={
        <span className="text-[9px] tabular-nums text-ui-soft">slot {pct}%</span>
      }
    >
      <p className="text-[8px] uppercase tracking-wide text-ui-soft">
        Net to plant (fee / margin on est. gross)
      </p>
      <p
        className="mt-1 break-all font-mono text-lg font-semibold leading-tight tracking-tight text-cyan-400 sm:text-xl"
        title="Estimated credits retained this slot from processing fee on accrual gross"
      >
        {formatPositiveCr(liveMarginCr)}
      </p>
      <p className="mt-1 font-mono text-[10px] tabular-nums text-cyan-500/80">
        {formatRate(feesCrPerSec, "+")} · est. cap {cap.toLocaleString()} cr / slot
      </p>

      <p className="mt-3 text-[8px] uppercase tracking-wide text-ui-soft">Context (same model)</p>
      <p className="mt-2 break-words font-mono text-[0.5625rem] font-semibold leading-tight tracking-tight sm:text-[0.625rem]">
        <span className="text-cyan-500/95 dark:text-cyan-400/90">Miner payout est. this slot:</span>{" "}
        <span className="tabular-nums text-red-600 dark:text-red-400">
          {formatOutflowCr(Math.min(maxMinerThisSlot, Math.floor(cap * minerRate * slotProgress)))}
        </span>
        <br />
        <span className="text-cyan-500/95 dark:text-cyan-400/90">at</span>{" "}
        <span className="tabular-nums text-red-600 dark:text-red-400">{formatRate(costCrPerSec, "−")}</span>
      </p>

      <div className="mt-3 border-t border-cyan-950/60 pt-2">
        <div
          className="h-1 w-full overflow-hidden rounded-full bg-zinc-800"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Mining slot elapsed"
        >
          <div
            className={`h-full rounded-full bg-cyan-700 ${reduceMotion ? "" : "transition-[width] duration-150"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="mt-1 text-[8px] text-ui-muted">
          {pct}% elapsed · proj. end-of-slot: +{projectedEndFees.toLocaleString()} cr retained /{" "}
          −{projectedEndCost.toLocaleString()} cr out
        </p>
      </div>

      {feeRate > 0 ? (
        <p className="mt-1.5 text-[8px] text-ui-muted">
          Fee rate {(feeRate * 100).toFixed(0)}% · margin on {cap.toLocaleString()} cr est. cap
        </p>
      ) : (
        <p className="mt-1.5 text-[8px] text-amber-600/80">
          Fee rate not available — connect to plant
        </p>
      )}
    </EconomyStatCard>
  );
}
