"use client";

import { EconomyStatCard } from "@/components/economy-stat-card";

/** Treasury outflow: minus sign + credits (magnitude only in arg). */
function formatTreasuryOutflowCr(n: number | undefined) {
  const v = Number.isFinite(n) ? Math.max(0, Math.floor(Number(n))) : 0;
  return `−${v.toLocaleString("en-US")} cr`;
}

function formatPositiveCr(n: number | undefined) {
  const v = Number.isFinite(n) ? Math.max(0, Math.floor(Number(n))) : 0;
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
  "Treasury outflow to players (plant raw purchase, refined collect). “Last slot” = previous completed UTC mining slot. " +
  "Gross = face value at settlement; fees retained by treasury; net = paid to miners. ";

const OUTFLOW_CLS =
  "truncate text-sm font-semibold tabular-nums text-red-600 dark:text-red-400";

export function EconomyMinerPayoutHero({
  lastCycleCr,
  totalCr,
  lastCycleGrossCr,
  lastCycleFeesCr,
  totalGrossCr,
  totalFeesCr,
  miningNextCycleAt,
  miningDeliveryPeriodSeconds,
}: {
  lastCycleCr: number | undefined;
  totalCr: number | undefined;
  lastCycleGrossCr?: number;
  lastCycleFeesCr?: number;
  totalGrossCr?: number;
  totalFeesCr?: number;
  miningNextCycleAt?: string;
  miningDeliveryPeriodSeconds?: number;
}) {
  const last = lastCycleCr ?? 0;
  const total = totalCr ?? 0;
  const lg = lastCycleGrossCr ?? 0;
  const lf = lastCycleFeesCr ?? 0;
  const tg = totalGrossCr ?? 0;
  const tf = totalFeesCr ?? 0;
  const nextShort = formatBoundaryShort(miningNextCycleAt);

  return (
    <EconomyStatCard
      title="Treasury miner settlements"
      hintTitle={`${HINT_PREFIX}${slotHint(miningDeliveryPeriodSeconds)} “Total” = all-time.`}
      headerRight={
        nextShort ? (
          <span className="text-ui-caption tabular-nums text-ui-soft" title="Current slot ends">
            ends {nextShort}
          </span>
        ) : null
      }
    >
      <div className="grid grid-cols-2 gap-x-3 divide-x divide-cyan-900/35">
        <div className="min-w-0 pr-3">
          <p className="text-ui-overline uppercase tracking-wide text-ui-soft">Last slot (net out)</p>
          <p className={`mt-0.5 ${OUTFLOW_CLS}`} title="Credits left treasury (net to miners)">
            {formatTreasuryOutflowCr(last)}
          </p>
          <p className="mt-2 text-ui-caption leading-snug text-ui-soft">
            <span className="text-ui-muted">Settlement gross</span> {formatPositiveCr(lg)}
            <br />
            <span className="text-red-600 dark:text-red-400">Fees retained</span>{" "}
            <span className="tabular-nums text-red-600 dark:text-red-400">{formatTreasuryOutflowCr(lf)}</span>
          </p>
        </div>
        <div className="min-w-0 pl-3">
          <p className="text-ui-overline uppercase tracking-wide text-ui-soft">All-time (net out)</p>
          <p className={`mt-0.5 ${OUTFLOW_CLS}`} title="All-time credits left treasury (net to miners)">
            {formatTreasuryOutflowCr(total)}
          </p>
          <p className="mt-2 text-ui-caption leading-snug text-ui-soft">
            <span className="text-ui-muted">Settlement gross</span> {formatPositiveCr(tg)}
            <br />
            <span className="text-red-600 dark:text-red-400">Fees retained</span>{" "}
            <span className="tabular-nums text-red-600 dark:text-red-400">{formatTreasuryOutflowCr(tf)}</span>
          </p>
        </div>
      </div>
    </EconomyStatCard>
  );
}
