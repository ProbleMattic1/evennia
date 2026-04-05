"use client";

import { useCallback, useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";

import { linearAccruingValue } from "@/lib/economy-world-meters";
import { getEconomyWorldState, type EconomyWorldPayload, type MarketCommodity } from "@/lib/ui-api";
import { intervalMs, isUiPollPaused } from "@/lib/ui-refresh-policy";

export function EconomyWorldPanel() {
  const reduceMotion = useReducedMotion();
  const [data, setData] = useState<EconomyWorldPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  const load = useCallback(async () => {
    try {
      const p = await getEconomyWorldState();
      setData(p);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "economy-world failed");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const ms = intervalMs("economyWorld", null);
    const id = window.setInterval(() => {
      if (!isUiPollPaused()) void load();
    }, ms);
    return () => window.clearInterval(id);
  }, [load]);

  useEffect(() => {
    if (reduceMotion) return;
    const id = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(id);
  }, [reduceMotion]);

  if (err) {
    return <p className="text-xs text-red-400">{err}</p>;
  }
  if (!data) {
    return <p className="text-xs text-ui-muted">Loading world economy…</p>;
  }

  const mining = data.world.mining ?? {};
  const ledger = data.world.ledger ?? {};
  const norm = data.world.simMetrics?.normalized;
  const auto = data.world.automation;
  const meter = data.meters[0];
  const stressMeter = data.meters.find((m) => m.id === "world_commodity_stress_index");
  const live =
    meter && !reduceMotion ? linearAccruingValue(meter, now) : (meter?.valueAtEnd ?? 0);
  const stressLive =
    stressMeter && !reduceMotion
      ? linearAccruingValue(stressMeter, now)
      : (stressMeter?.valueAtEnd ??
          (norm != null ? Math.round(norm.commodityPressure * 100) : null));

  return (
    <section className="mb-4 rounded border border-cyan-900/40 bg-zinc-950/90 p-3">
      <p className="text-ui-caption uppercase tracking-widest text-ui-muted">World economy</p>
      <p className="mt-1 font-mono text-sm tabular-nums text-cyber-cyan">
        {Math.floor(live).toLocaleString()}<span className="text-ui-muted">cr</span>
        <span className="ml-2 text-xs text-ui-soft">slot meter (implied)</span>
      </p>
      {stressLive != null ? (
        <p className="mt-1 font-mono text-xs tabular-nums text-amber-400/90">
          Commodity stress {Math.round(stressLive)}
          <span className="text-ui-muted">/100</span>
          {norm != null ? (
            <span className="ml-2 text-ui-soft">
              logi {(norm.logisticsPressure * 100).toFixed(0)} prop{" "}
              {(norm.propertyPressure * 100).toFixed(0)}
            </span>
          ) : null}
        </p>
      ) : null}
      {auto?.phase != null ? (
        <p className="mt-1 text-xs text-ui-muted">
          Automation phase <span className="font-mono text-cyber-cyan">{auto.phase}</span>
          {auto.globalPriceMultiplier != null ? (
            <span className="ml-2 font-mono">×{auto.globalPriceMultiplier.toFixed(2)} price</span>
          ) : null}
        </p>
      ) : null}
      <div className="mt-2 grid gap-1 text-xs text-ui-muted sm:grid-cols-2">
        <span>sites {mining.siteCount ?? 0}</span>
        <span>active {mining.activeSiteCount ?? 0}</span>
        <span>producing {mining.producingSiteCount ?? 0}</span>
        <span>stored (bid) {(mining.storedValueBidCr ?? 0).toLocaleString()}cr</span>
        <span>treasury {(ledger.treasuryBalanceCr ?? 0).toLocaleString()}cr</span>
        <span>player mass {(ledger.playerCreditsMassCr ?? 0).toLocaleString()}cr</span>
        {data.world.simMetrics?.logistics &&
        typeof data.world.simMetrics.logistics === "object" &&
        "dueCount" in data.world.simMetrics.logistics ? (
          <span>
            haulers due{" "}
            {String((data.world.simMetrics.logistics as { dueCount?: number }).dueCount ?? "—")}
          </span>
        ) : null}
        {data.world.simMetrics?.propertyOps &&
        typeof data.world.simMetrics.propertyOps === "object" &&
        "activeHoldingCount" in data.world.simMetrics.propertyOps ? (
          <span>
            property ops{" "}
            {String(
              (data.world.simMetrics.propertyOps as { activeHoldingCount?: number }).activeHoldingCount ??
                "—",
            )}
          </span>
        ) : null}
      </div>
      {data.market.length > 0 ? (
        <div className="mt-3 border-t border-cyan-900/30 pt-2">
          <p className="text-ui-caption uppercase tracking-widest text-ui-muted">Market snapshot (economy-world)</p>
          <div className="mt-1 max-h-[min(240px,40vh)] overflow-auto rounded border border-cyan-900/40">
            <table className="w-full border-collapse text-left text-[10px]">
              <thead>
                <tr className="border-b border-cyan-900/50 bg-zinc-950/90">
                  <th className="px-1.5 py-1 font-medium text-cyber-cyan">Commodity</th>
                  <th className="px-1.5 py-1 text-right font-medium text-cyber-cyan">Sell/t</th>
                  <th className="px-1.5 py-1 text-right font-medium text-cyber-cyan">Buy/t</th>
                </tr>
              </thead>
              <tbody>
                {data.market.map((c: MarketCommodity) => (
                  <tr key={c.key} className="border-b border-zinc-800/60 last:border-0">
                    <td className="max-w-[10rem] truncate px-1.5 py-0.5 text-foreground" title={c.name}>
                      {c.name}
                    </td>
                    <td className="px-1.5 py-0.5 text-right font-mono tabular-nums text-ui-muted">
                      {c.sellPriceCrPerTon.toLocaleString()}
                    </td>
                    <td className="px-1.5 py-0.5 text-right font-mono tabular-nums text-ui-muted">
                      {c.buyPriceCrPerTon.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </section>
  );
}
