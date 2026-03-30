"use client";

import { useReducedMotion } from "motion/react";

import type { ControlSurfaceState } from "@/lib/control-surface-api";
import { treasuryMiningSlotElapsedSec } from "@/lib/economy-dashboard-derive";
import { EconomyStatCard } from "@/components/economy-stat-card";
import { useOdometerInt } from "@/lib/use-odometer-value";
import { useServerAnchoredTimeMs } from "@/lib/use-server-anchored-time";

const HINT =
  "This UTC mining slot: settlement gross (ore/refined face value), fees retained by treasury, net paid to miners (= gross − fees). " +
  "Totals jump when a settlement occurs; control-surface poll refreshes them. " +
  "Avg cr/s = amount so far ÷ elapsed time in slot (falls during quiet periods).";

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

function formatOutflowCr(n: number) {
  const v = Math.max(0, Math.floor(Number(n) || 0));
  return `−${v.toLocaleString("en-US")} cr`;
}

function formatPositiveCr(n: number) {
  const v = Math.max(0, Math.floor(Number(n) || 0));
  return `${v.toLocaleString("en-US")} cr`;
}

function formatOutflowRate(crPerSec: number) {
  if (!Number.isFinite(crPerSec) || crPerSec <= 0) return "−0 cr/s";
  if (crPerSec >= 1) return `−${crPerSec.toFixed(2)} cr/s`;
  return `−${(crPerSec * 100).toFixed(1)} ¢/s`;
}

function formatPositiveRate(crPerSec: number) {
  if (!Number.isFinite(crPerSec) || crPerSec <= 0) return "0 cr/s";
  if (crPerSec >= 1) return `${crPerSec.toFixed(2)} cr/s`;
  return `${(crPerSec * 100).toFixed(1)} ¢/s`;
}

export function EconomyTreasuryLiveFlowCard({ data }: { data: ControlSurfaceState }) {
  const reduceMotion = useReducedMotion();
  const nowMs = useServerAnchoredTimeMs(data.serverTimeIso);
  const nextShort = formatBoundaryShort(data.miningNextCycleAt);

  const net = data.minerSettlementThisSlotNetCr ?? 0;
  const gross = data.minerSettlementThisSlotGrossCr ?? 0;
  const fees = data.minerSettlementThisSlotFeesCr ?? 0;

  const netOdoRaw = useOdometerInt(net, 40);
  const grossOdoRaw = useOdometerInt(gross, 40);
  const feesOdoRaw = useOdometerInt(fees, 40);
  const displayNet = reduceMotion ? net : netOdoRaw;
  const displayGross = reduceMotion ? gross : grossOdoRaw;
  const displayFees = reduceMotion ? fees : feesOdoRaw;

  const elapsedSec = treasuryMiningSlotElapsedSec(data, nowMs);
  const impliedNetPerSec = net / elapsedSec;
  const impliedGrossPerSec = gross / elapsedSec;
  const impliedFeesPerSec = fees / elapsedSec;
  const derivedNet = Math.max(0, gross - fees);

  return (
    <EconomyStatCard
      title="Treasury cash flow (this slot)"
      hintTitle={HINT}
      headerRight={
        nextShort ? (
          <span className="text-ui-caption tabular-nums text-ui-soft" title="Mining grid boundary">
            ends {nextShort}
          </span>
        ) : null
      }
    >
      <div className="min-w-0">
        <p className="text-ui-overline uppercase tracking-wide text-ui-soft">Net to miners (gross − fees)</p>
        <p
          className="mt-0.5 truncate font-mono text-base font-semibold tabular-nums text-red-600 dark:text-red-400"
          title="Treasury outflow this slot"
        >
          {formatOutflowCr(displayNet)}
        </p>
        <p className="mt-2 text-ui-caption leading-relaxed text-ui-soft">
          <span className="text-ui-accent-readable dark:text-cyber-cyan/90">Ore / settlement gross</span>{" "}
          <span className="font-mono tabular-nums text-ui-accent-readable dark:text-cyber-cyan">
            {formatPositiveCr(displayGross)}
          </span>
          <span className="text-ui-muted"> · </span>
          <span className="text-red-600 dark:text-red-400">Fees retained</span>{" "}
          <span className="font-mono tabular-nums text-red-600 dark:text-red-400">
            {formatOutflowCr(displayFees)}
          </span>
          <span className="text-ui-muted"> · </span>
          <span className="text-ui-muted">
            Check: gross − fees = {formatPositiveCr(derivedNet)}
            {derivedNet !== net ? (
              <span className="text-amber-600 dark:text-amber-500"> · ledger net {formatPositiveCr(net)}</span>
            ) : null}
          </span>
        </p>
      </div>
      <div className="mt-3 border-t border-cyan-950/60 pt-2">
        <p className="text-ui-overline uppercase tracking-wider text-ui-muted">Avg rate this slot (live clock)</p>
        <p className="mt-0.5 break-words font-mono text-ui-caption font-semibold leading-tight tracking-tight tabular-nums sm:text-xs">
          <span className="text-red-600 dark:text-red-400">Net out {formatOutflowRate(impliedNetPerSec)}</span>
          <span className="text-ui-soft"> · Gross {formatPositiveRate(impliedGrossPerSec)}</span>
          <span className="text-red-500/80 dark:text-red-400/80">
            {" "}
            · Fees {formatPositiveRate(impliedFeesPerSec)} (retained)
          </span>
        </p>
        <p className="mt-1 text-ui-overline text-ui-muted">
          Elapsed {Math.floor(elapsedSec / 60)}m {Math.floor(elapsedSec % 60)}s · updates on poll + clock
        </p>
      </div>
    </EconomyStatCard>
  );
}
