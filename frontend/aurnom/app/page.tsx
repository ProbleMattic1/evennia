"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Countdown } from "@/components/countdown";
import { MissionBoard } from "@/components/mission-board";

import { volumeTierStyle, rarityTierStyle } from "@/lib/mine-tier-styles";
import { dashboardAckAlert, getDashboardState, getResources, mineDeploy, playTravel } from "@/lib/ui-api";
import type { DashboardInventoryItem, ResourceEntry } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

const EVENNIA_ORIGIN = process.env.NEXT_PUBLIC_EVENNIA_ORIGIN ?? "";

const ABILITY_ORDER = ["str", "dex", "con", "int", "wis", "cha"] as const;

const ABILITY_COLORS: Record<string, string> = {
  str: "bg-red-100 text-red-800 ring-red-200/70 dark:bg-red-950/50 dark:text-red-300 dark:ring-red-800/40",
  dex: "bg-amber-100 text-amber-800 ring-amber-200/70 dark:bg-amber-950/50 dark:text-amber-300 dark:ring-amber-800/40",
  con: "bg-emerald-100 text-emerald-800 ring-emerald-200/70 dark:bg-emerald-950/50 dark:text-emerald-300 dark:ring-emerald-800/40",
  int: "bg-sky-100 text-sky-800 ring-sky-200/70 dark:bg-sky-950/50 dark:text-sky-300 dark:ring-sky-800/40",
  wis: "bg-violet-100 text-violet-800 ring-violet-200/70 dark:bg-violet-950/50 dark:text-violet-300 dark:ring-violet-800/40",
  cha: "bg-rose-100 text-rose-800 ring-rose-200/70 dark:bg-rose-950/50 dark:text-rose-300 dark:ring-rose-800/40",
};

function formatAbilityModifier(mod: number): string {
  return mod >= 0 ? `+${mod}` : `${mod}`;
}

/** Shared layout + type scale for header stat tiles (economy, combat, abilities). */
const DASH_STAT_TILE = "shrink-0 rounded-lg px-2 py-1 ring-1";
const DASH_STAT_DT = "text-[10px] font-medium uppercase tracking-wide leading-tight";
const DASH_STAT_DD =
  "mt-0.5 font-mono text-xs tabular-nums leading-tight text-zinc-800 dark:text-zinc-200";
const DASH_STAT_DD_HP =
  "mt-0.5 font-mono text-xs tabular-nums leading-tight text-emerald-800 dark:text-emerald-300";
const DASH_STAT_CR = "text-amber-600 dark:text-amber-400";
const DASH_STAT_DD_MOD = "text-zinc-600 dark:text-zinc-400";

const PROPERTY_ZONE_LABEL: Record<string, string> = {
  residential: "Residential",
  commercial: "Commercial",
  industrial: "Industrial",
};

/** Strip bracketed segments containing "Unknown" from ship summary (e.g. [Unknown / Unknown]). */
function formatShipSummary(summary: string): string {
  return summary
    .replace(/\s*\[[^\]]*Unknown[^\]]*\]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function resourceNameByKey(resources: ResourceEntry[]): Record<string, string> {
  return Object.fromEntries(resources.map((r) => [r.key, r.name]));
}

/** Live UTC calendar date and time (server world clock). Client-only after mount to avoid hydration mismatch. */
function UtcDailyClock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    const tick = () => setNow(new Date());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  const formatted = useMemo(() => {
    if (!now) return "";
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "UTC",
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(now);
  }, [now]);
  return (
    <div className="text-left">
      <p className="text-[10px] font-medium uppercase tracking-wide leading-tight text-zinc-500 dark:text-zinc-400">
        World time (UTC)
      </p>
      <time
        dateTime={now ? now.toISOString() : undefined}
        className="mt-1 block min-h-[1rem] font-mono text-[11px] tabular-nums leading-tight text-zinc-600 dark:text-zinc-400"
      >
        {now ? formatted : "—"}
      </time>
    </div>
  );
}

export default function Home() {
  const router = useRouter();
  const loader = useCallback(() => getDashboardState(), []);
  const { data, error, loading, reload } = useUiResource(loader);

  const resourcesLoader = useCallback(() => getResources(), []);
  const { data: resourcesData } = useUiResource(resourcesLoader);

  const [deployPackageId, setDeployPackageId] = useState<number | null>(null);
  const [deployClaimId, setDeployClaimId] = useState<number | null>(null);
  const [deployBusy, setDeployBusy] = useState(false);
  const [deployError, setDeployError] = useState<string | null>(null);
  const [deploySuccess, setDeploySuccess] = useState<string | null>(null);

  const packages = useMemo(() => {
    const rows: DashboardInventoryItem[] = [];
    for (const i of data?.inventory ?? []) {
      if (!i.isMiningPackage) continue;
      const idList = i.stacked && i.ids?.length ? i.ids : [i.id];
      for (const id of idList) {
        rows.push({ ...i, id });
      }
    }
    return rows;
  }, [data?.inventory]);

  const claims = useMemo(() => {
    const rows: DashboardInventoryItem[] = [];
    for (const i of data?.inventory ?? []) {
      if (!i.isMiningClaim) continue;
      const idList = i.stacked && i.ids?.length ? i.ids : [i.id];
      for (const id of idList) {
        rows.push({ ...i, id });
      }
    }
    return rows;
  }, [data?.inventory]);
  const canDeploy = !!(data?.character && packages.length > 0 && claims.length > 0);

  async function handleDeploy() {
    if (deployPackageId == null || deployClaimId == null) return;
    setDeployError(null);
    setDeploySuccess(null);
    setDeployBusy(true);
    try {
      const res = await mineDeploy({ packageId: deployPackageId, claimId: deployClaimId });
      const msg = res?.message;
      setDeploySuccess(typeof msg === "string" ? msg : "Mine deployed.");
      setDeployPackageId(null);
      setDeployClaimId(null);
      reload();
    } catch (err) {
      setDeployError(String(err instanceof Error ? err.message : "Deploy failed"));
    } finally {
      setDeployBusy(false);
    }
  }

  async function handleAckAlert(alertId: string) {
    try {
      await dashboardAckAlert({ alertId });
      reload();
    } catch {
      // no-op; dashboard reload path remains available
    }
  }

  async function handleVisitMine(destination: string) {
    try {
      await playTravel({ destination });
    } catch {
      // Best-effort bridge call; still route so UI remains usable.
    } finally {
      router.push(`/play?room=${encodeURIComponent(destination)}`);
    }
  }

  const resourceNames = useMemo(
    () => (resourcesData?.resources ? resourceNameByKey(resourcesData.resources) : {}),
    [resourcesData]
  );

  useEffect(() => {
    const mines = data?.mines ?? [];
    const overdue = mines.some((m) => {
      if (!m.nextCycleAt) return false;
      return new Date(m.nextCycleAt).getTime() <= Date.now();
    });
    if (!overdue) return;
    const id = setInterval(() => reload(), 15000);
    return () => clearInterval(id);
  }, [data?.mines, reload]);

  function SectionDivider() {
    return <hr className="section-divider" aria-hidden />;
  }

  if (loading) {
    return (
      <main className="main-content">
        <div className="space-y-2 border-b border-zinc-200 px-2 py-3 dark:border-cyan-900/50">
          <p className="text-sm text-zinc-500 dark:text-cyan-500/80">Loading dashboard…</p>
          <UtcDailyClock />
        </div>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="main-content">
        <div className="space-y-2 border-b border-zinc-200 px-2 py-3 dark:border-cyan-900/50">
          <p className="text-sm text-red-600 dark:text-red-400">
            Failed to load dashboard: {error ?? "Unknown error"}
          </p>
          <UtcDailyClock />
        </div>
      </main>
    );
  }

  return (
    <main className="main-content">
      <header className="page-header border-b border-zinc-200 py-3 pl-2 dark:border-cyan-900/50">
        <div className="px-2 pr-4">
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Aurnom</h1>
          <p className="mt-0.5 text-[12px] text-zinc-500 dark:text-zinc-400">
            {data.character
              ? `Signed in as ${data.character.key}. Location: ${data.character.room ?? "Unknown"}.`
              : "Character dashboard and entry point for the Evennia-powered world."}
          </p>
          <div className="mt-1.5">
            <UtcDailyClock />
          </div>
        </div>
        {data.character ? (
          <dl className="mt-2 flex flex-wrap items-stretch gap-x-1.5 gap-y-1.5 border-t border-zinc-200 px-2 pt-2 dark:border-cyan-900/50">
            {data.credits !== null ? (
              <div
                className={`${DASH_STAT_TILE} ring-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:ring-amber-700/30`}
              >
                <dt className={`${DASH_STAT_DT} text-amber-700 dark:text-amber-400`}>Credits</dt>
                <dd className={DASH_STAT_DD}>
                  {data.credits.toLocaleString()}
                  <span className={DASH_STAT_CR}>cr</span>
                </dd>
              </div>
            ) : null}
            {(data.miningEstimatedValuePerCycle ?? 0) > 0 ||
            (data.miningTotalStoredValue ?? 0) > 0 ||
            (data.properties?.length ?? 0) > 0 ? (
              <>
                <div
                  className={`${DASH_STAT_TILE} ring-teal-200 bg-teal-50 dark:bg-teal-950/30 dark:ring-teal-700/30`}
                >
                  <dt className={`${DASH_STAT_DT} text-teal-700 dark:text-teal-400`}>
                    Est Cr/cycle
                  </dt>
                  <dd className={DASH_STAT_DD}>
                    {(data.miningEstimatedValuePerCycle ?? 0).toLocaleString()}
                    <span className={DASH_STAT_CR}>cr</span>
                  </dd>
                </div>
                <div
                  className={`${DASH_STAT_TILE} ring-emerald-200 bg-emerald-50 dark:bg-emerald-950/30 dark:ring-emerald-700/30`}
                >
                  <dt className={`${DASH_STAT_DT} text-emerald-700 dark:text-emerald-400`}>
                    Res Val
                  </dt>
                  <dd className={DASH_STAT_DD}>
                    {(data.miningTotalStoredValue ?? 0).toLocaleString()}
                    <span className={DASH_STAT_CR}>cr</span>
                  </dd>
                </div>
                {(data.properties?.length ?? 0) > 0 && (data.propertyReferenceListValueTotalCr ?? 0) > 0 ? (
                  <div
                    className={`${DASH_STAT_TILE} ring-fuchsia-200 bg-fuchsia-50 dark:bg-fuchsia-950/30 dark:ring-fuchsia-700/30`}
                  >
                    <dt className={`${DASH_STAT_DT} text-fuchsia-700 dark:text-fuchsia-400`}>
                      Tot Prop Val
                    </dt>
                    <dd className={DASH_STAT_DD}>
                      {(data.propertyReferenceListValueTotalCr ?? 0).toLocaleString()}
                      <span className={DASH_STAT_CR}>cr</span>
                    </dd>
                  </div>
                ) : null}
              </>
            ) : null}
            <div
              className={`${DASH_STAT_TILE} ring-sky-200 bg-sky-50 dark:bg-sky-950/30 dark:ring-sky-700/30`}
            >
              <dt className={`${DASH_STAT_DT} text-sky-700 dark:text-sky-400`}>Armor</dt>
              <dd className={DASH_STAT_DD}>{data.character.armorClass}</dd>
            </div>
            {data.character.vitals.hp ? (
              <div
                className={`${DASH_STAT_TILE} ring-emerald-200 bg-emerald-50 dark:bg-emerald-950/30 dark:ring-emerald-700/30`}
              >
                <dt className={`${DASH_STAT_DT} text-emerald-700 dark:text-emerald-400`}>HP</dt>
                <dd className={DASH_STAT_DD_HP}>
                  {data.character.vitals.hp.current}
                  {data.character.vitals.hp.max != null ? (
                    <>/{data.character.vitals.hp.max}</>
                  ) : null}
                </dd>
              </div>
            ) : null}
            {ABILITY_ORDER.map((key) => {
              const row = data.character.abilities[key];
              if (!row) return null;
              const label = key.toUpperCase();
              const mod = formatAbilityModifier(row.abilityMod);
              return (
                <div
                  key={key}
                  className={`${DASH_STAT_TILE} ${
                    ABILITY_COLORS[key] ??
                    "bg-zinc-100 text-zinc-800 ring-zinc-200/70 dark:bg-zinc-800 dark:text-zinc-200 dark:ring-zinc-600/50"
                  }`}
                  aria-label={`${label} ${row.score}, modifier ${mod}`}
                >
                  <dt className={DASH_STAT_DT}>{label}</dt>
                  <dd className={DASH_STAT_DD}>
                    <span title={`${label} score`}>{row.score}</span>
                    <span className={DASH_STAT_DD_MOD} title="Ability modifier">
                      {mod}
                    </span>
                  </dd>
                </div>
              );
            })}
          </dl>
        ) : null}
      </header>

      {!data.authenticated ? (
        <p className="mx-2 mt-2 rounded border border-amber-200/60 bg-amber-50/80 px-2 py-1.5 text-[12px] text-amber-800 dark:border-cyan-700/50 dark:bg-cyan-950/30 dark:text-amber-200">
          Sign in on the game server with the same browser session to see your character, credits, and
          inventory here.
          {EVENNIA_ORIGIN ? (
            <>
              {" "}
              <a href={`${EVENNIA_ORIGIN.replace(/\/$/, "")}/`} className="font-medium underline dark:text-cyan-400 dark:hover:text-cyan-300">
                Open game site
              </a>
            </>
          ) : null}
        </p>
      ) : null}

      {data.authenticated && data.message ? (
        <p className="mx-2 mt-2 rounded border border-amber-200/60 bg-amber-50/80 px-2 py-1.5 text-[12px] text-amber-800 dark:border-cyan-700/50 dark:bg-cyan-950/30 dark:text-amber-200">
          {data.message}
        </p>
      ) : null}

      {data.character && data.groupedAlerts ? (
        <>
          <SectionDivider />
          <section className="mx-2 rounded-lg border border-red-200/60 bg-red-50/40 px-3 py-2 dark:border-red-800/40 dark:bg-red-950/20">
            <details className="group" open>
              <summary className="section-label flex cursor-pointer list-none items-center justify-between [&::-webkit-details-marker]:hidden">
                <span>System Alerts</span>
                <svg
                  className="size-3 shrink-0 transition-transform group-open:rotate-90"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </summary>
              <div className="mt-1">
                {(["critical", "warning", "info"] as const).map((sev) => {
                  const rows = data.groupedAlerts?.[sev] ?? [];
                  if (!rows.length) return null;
                  return (
                    <div key={sev} className="mt-2">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-600 dark:text-zinc-300">
                        {sev}
                      </p>
                      <ul className="mt-1 space-y-1">
                        {rows.map((a) => (
                          <li
                            key={a.id}
                            className={`rounded border px-2 py-1 ${
                              sev === "critical"
                                ? "border-red-300 bg-red-100/70 dark:border-red-700/60 dark:bg-red-900/30"
                                : sev === "warning"
                                  ? "border-amber-300 bg-amber-100/70 dark:border-amber-700/60 dark:bg-amber-900/30"
                                  : "border-sky-300 bg-sky-100/70 dark:border-sky-700/60 dark:bg-sky-900/30"
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <p className="text-[12px] font-semibold text-zinc-900 dark:text-zinc-100">
                                  {a.title} {a.source ? `(${a.source})` : ""}
                                </p>
                                {a.detail ? (
                                  <p className="text-[12px] text-zinc-700 dark:text-zinc-300">{a.detail}</p>
                                ) : null}
                                <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                                  {new Date(a.createdAt).toLocaleString()}
                                </p>
                              </div>
                              <button
                                type="button"
                                onClick={() => handleAckAlert(a.id)}
                                className="shrink-0 rounded border border-zinc-400 bg-zinc-100 px-2 py-0.5 text-[11px] hover:bg-zinc-200 dark:border-zinc-600 dark:bg-zinc-800 dark:hover:bg-zinc-700"
                              >
                                Acknowledge
                              </button>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  );
                })}
              </div>
            </details>
          </section>
        </>
      ) : null}

      {data.character && data.missions ? (
        <>
          <SectionDivider />
          <MissionBoard missions={data.missions} onChanged={reload} />
        </>
      ) : null}

      {data.character ? (
        <>
          <SectionDivider />
          <section className="mx-2 rounded-lg border border-violet-200/60 bg-violet-50/50 px-3 py-2 dark:border-violet-800/40 dark:bg-violet-950/20">
            <details className="group">
              <summary className="section-label flex cursor-pointer list-none items-center justify-between [&::-webkit-details-marker]:hidden">
                <span>Inventory</span>
                <svg
                  className="size-3 shrink-0 transition-transform group-open:rotate-90"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </summary>
              <div className="mt-1">
            {data.inventory.length === 0 ? (
              <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">You are not carrying any items.</p>
            ) : (
              <ul className="mt-1 space-y-0.5">
                {data.inventory.map((item, i) => (
                  <li
                    key={
                      item.stacked && item.ids?.length
                        ? `inv-stack-${item.ids.join("-")}`
                        : String(item.id)
                    }
                    className={`rounded py-1.5 px-2 -mx-2 ${
                      i % 2 === 0 ? "bg-violet-100/40 dark:bg-violet-950/30" : "bg-white/50 dark:bg-violet-900/10"
                    }`}
                  >
                    <div className="min-w-0 space-y-0.5">
                      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                        <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                          {item.key}
                          {(item.count ?? 1) > 1 ? (
                            <span className="ml-1.5 tabular-nums text-zinc-500 dark:text-zinc-400">
                              ×{item.count}
                            </span>
                          ) : null}
                        </span>
                        {item.isMiningPackage && item.estimatedValue != null ? (
                          <span className="text-[11px] tabular-nums text-amber-700/90 dark:text-amber-400/90">
                            ~{item.estimatedValue.toLocaleString()}{" "}
                            <span className="text-amber-600 dark:text-amber-500">cr</span>
                          </span>
                        ) : null}
                      </div>
                      {item.description ? (
                        <p className="text-[12px] leading-snug text-zinc-500 break-words dark:text-cyan-500/85">
                          {item.description}
                        </p>
                      ) : null}
                    </div>
                    {item.isMiningClaim && item.claimSpecs ? (
                      <div className="mt-1 space-y-0.5">
                        <p className="text-[12px] text-zinc-500 dark:text-cyan-500/80">
                          {item.claimSpecs.roomKey}
                          {item.claimSpecs.volumeTier || item.claimSpecs.resourceRarityTier ? (
                            <> · {[item.claimSpecs.volumeTier, item.claimSpecs.resourceRarityTier].filter(Boolean).join(" / ")}</>
                          ) : null}
                          {" · "}
                          {item.claimSpecs.baseOutputTons}t/cycle · Hazard {item.claimSpecs.hazardLabel}
                        </p>
                        {Object.keys(item.claimSpecs.composition).length > 0 ? (
                          <p className="text-[12px] text-zinc-500 dark:text-cyan-500/80">
                            {Object.entries(item.claimSpecs.composition)
                              .map(
                                ([k, v]) =>
                                  `${resourceNames[k] ?? k} ${Math.round(v * 100)}%`
                              )
                              .join(", ")}
                          </p>
                        ) : null}
                        <p className="text-[12px] font-medium text-zinc-600 dark:text-cyan-400/90">
                          Est. ~{item.claimSpecs.estimatedValuePerCycle.toLocaleString()}{" "}
                          <span className="text-amber-700 dark:text-amber-400">cr</span>/cycle
                        </p>
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
              </div>
            </details>
          </section>
        </>
      ) : null}

      {data.character && canDeploy ? (
        <>
          <SectionDivider />
          <section className="mx-2 rounded-lg border border-amber-200/60 bg-amber-50/50 px-3 py-2 dark:border-amber-800/40 dark:bg-amber-950/20">
            <h2 className="section-label">Deploy Mine</h2>
            <p className="mt-1 text-[12px] text-zinc-500 dark:text-cyan-500/80">
              Choose a package and claim to deploy a mining operation.
            </p>
            <div className="mt-2 flex flex-wrap gap-3">
              <div>
                <label className="block text-[12px] font-medium text-zinc-500 dark:text-cyan-400/90">Package</label>
                <select
                  className="mt-0.5 rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-800 dark:border-cyan-700/50 dark:bg-zinc-900 dark:text-zinc-200"
                  value={deployPackageId ?? ""}
                  onChange={(e) =>
                    setDeployPackageId(e.target.value ? Number(e.target.value) : null)
                  }
                >
                  <option value="">Select…</option>
                  {packages.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.key}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[12px] font-medium text-zinc-500 dark:text-cyan-400/90">Claim</label>
                <select
                  className="mt-0.5 rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-800 dark:border-cyan-700/50 dark:bg-zinc-900 dark:text-zinc-200"
                  value={deployClaimId ?? ""}
                  onChange={(e) =>
                    setDeployClaimId(e.target.value ? Number(e.target.value) : null)
                  }
                >
                  <option value="">Select…</option>
                  {claims.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.key}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  className="rounded bg-zinc-800 px-3 py-1 text-sm text-white hover:bg-zinc-700 disabled:opacity-50 dark:bg-cyan-700 dark:hover:bg-cyan-600"
                  disabled={deployBusy || deployPackageId == null || deployClaimId == null}
                  onClick={handleDeploy}
                >
                  {deployBusy ? "Deploying…" : "Deploy"}
                </button>
              </div>
            </div>
            {deployError ? (
              <p className="mt-2 text-[12px] text-red-600 dark:text-red-400">{deployError}</p>
            ) : null}
            {deploySuccess ? (
              <p className="mt-2 text-[12px] text-emerald-600 dark:text-emerald-400">{deploySuccess}</p>
            ) : null}
          </section>
        </>
      ) : null}

      {data.character ? (
        <>
          <SectionDivider />
          <section className="mx-2 rounded-lg border border-sky-200/60 bg-sky-50/50 px-3 py-2 dark:border-sky-800/40 dark:bg-sky-950/20">
            <details className="group">
              <summary className="section-label flex cursor-pointer list-none items-center justify-between [&::-webkit-details-marker]:hidden">
                <span>Ships</span>
                <svg
                  className="size-3 shrink-0 transition-transform group-open:rotate-90"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </summary>
              <div className="mt-1">
            {data.ships.length === 0 ? (
              <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                No owned ships yet. Visit the{" "}
                <Link
                  href="/shop?room=Meridian%20Civil%20Shipyard"
                  className="text-sky-700 underline hover:text-sky-900 dark:text-sky-400 dark:hover:text-sky-300"
                >
                  shipyard
                </Link>{" "}
                to buy one.
              </p>
            ) : (
              <ul className="mt-1 space-y-1">
                {data.ships.map((ship, i) => (
                  <li
                    key={
                      ship.stacked && ship.ids?.length
                        ? `ship-stack-${ship.ids.join("-")}`
                        : String(ship.id)
                    }
                    className={`rounded py-1.5 px-2 -mx-2 ${
                      i % 2 === 0 ? "bg-sky-100/40 dark:bg-sky-950/30" : "bg-white/50 dark:bg-sky-900/10"
                    }`}
                  >
                    <div className="min-w-0 space-y-0.5">
                      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                        <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                          {ship.key}
                          {(ship.count ?? 1) > 1 ? (
                            <span className="ml-1.5 tabular-nums text-zinc-500 dark:text-zinc-400">
                              ×{ship.count}
                            </span>
                          ) : null}
                        </span>
                      </div>
                      {(() => {
                        const formatted = formatShipSummary(ship.summary);
                        return formatted && formatted !== ship.key ? (
                          <p className="text-[12px] leading-snug text-zinc-500 break-words dark:text-cyan-500/80">
                            {formatted}
                          </p>
                        ) : null;
                      })()}
                      {ship.stacked && ship.locations?.length ? (
                        <p className="text-[11px] leading-snug text-zinc-500 break-words dark:text-cyan-500/75">
                          <span className="font-medium text-zinc-400 dark:text-zinc-500">Locations: </span>
                          {ship.locations.map((loc, i) => (
                            <span key={i}>
                              {i > 0 ? ", " : null}
                              {loc ?? "—"}
                            </span>
                          ))}
                        </p>
                      ) : (
                        <p className="text-[11px] leading-snug text-zinc-500 break-words dark:text-cyan-500/75">
                          <span className="font-medium text-zinc-400 dark:text-zinc-500">Location: </span>
                          {ship.location ?? "—"}
                        </p>
                      )}
                      <p className="text-[11px] leading-snug text-zinc-400 dark:text-cyan-500/70">
                        {ship.state ?? "—"} · {ship.pilot ?? "—"}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
              </div>
            </details>
          </section>
        </>
      ) : null}

      {data.character && data.mines && data.mines.length > 0 ? (
        <>
          <SectionDivider />
          <section className="mx-2 rounded-lg border border-emerald-200/60 bg-emerald-50/50 px-3 py-2 dark:border-emerald-800/40 dark:bg-emerald-950/20">
            <details className="group">
              <summary className="section-label flex cursor-pointer list-none items-center justify-between [&::-webkit-details-marker]:hidden">
                <span>My Mines</span>
                <svg
                  className="size-3 shrink-0 transition-transform group-open:rotate-90"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </summary>
              <div className="mt-1">
            <ul className="space-y-1">
              {data.mines.map((mine, i) => (
                <li
                  key={mine.key}
                  className={`rounded py-1.5 px-2 -mx-2 ${
                    i % 2 === 0 ? "bg-emerald-100/40 dark:bg-emerald-950/30" : "bg-white/50 dark:bg-emerald-900/10"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span
                      className={`rounded px-1.5 py-0.5 font-mono text-[11px] font-medium ${
                        mine.active
                          ? "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-400 dark:ring-emerald-700/50"
                          : "bg-red-100 text-red-800 ring-1 ring-red-300 dark:bg-red-950/50 dark:text-red-300 dark:ring-red-700/50"
                      }`}
                    >
                      {mine.active ? "Active" : "Inactive"}
                    </span>
                    <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">{mine.key}</span>
                    {mine.volumeTier ? (
                      <span
                        className={`rounded px-1.5 py-0.5 font-mono text-[11px] font-medium ${
                          volumeTierStyle(mine.volumeTierCls).badge
                        }`}
                      >
                        {mine.volumeTier}
                      </span>
                    ) : null}
                    {mine.resourceRarityTier ? (
                      <span
                        className={`rounded px-1.5 py-0.5 font-mono text-[11px] font-medium ${
                          rarityTierStyle(mine.resourceRarityTierCls).badge
                        }`}
                      >
                        {mine.resourceRarityTier}
                      </span>
                    ) : null}
                    <span className="text-[12px] text-zinc-500 dark:text-cyan-500/80">
                      {mine.location ?? "—"}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[12px] text-zinc-400 dark:text-cyan-500/70">
                    Storage: {mine.storageUsed}/{mine.storageCapacity}t
                    {mine.nextCycleAt ? (
                      <>
                        {" "}
                        ·{" "}
                        <Countdown
                          targetIso={mine.nextCycleAt}
                          prefix="Next cycle:"
                          onExpired={reload}
                        />
                      </>
                    ) : null}
                  </p>
                  {((mine.estimatedOutputTons != null && mine.estimatedOutputTons > 0) ||
                    (mine.estimatedValuePerCycle != null && mine.estimatedValuePerCycle > 0)) ? (
                    <p className="text-[12px] text-zinc-500 dark:text-cyan-500/80">
                      Est. ~{mine.estimatedOutputTons != null ? mine.estimatedOutputTons.toFixed(1) : "—"} t/cycle
                      {" · "}
                      ~{(mine.estimatedValuePerCycle ?? 0).toLocaleString()}{" "}
                      <span className="text-amber-600 dark:text-amber-400">cr</span>/cycle
                    </p>
                  ) : null}
                  {mine.rig ? (
                    <p className="text-[12px] text-zinc-400 dark:text-cyan-500/70">
                      Rig: {mine.rig} ({mine.rigWear ?? 0}% wear)
                    </p>
                  ) : null}
                  {Object.keys(mine.composition).length > 0 ? (
                    <p className="text-[12px] text-zinc-400 dark:text-cyan-500/70">
                      Produces:{" "}
                      {Object.entries(mine.composition)
                        .map(
                          ([k, v]) =>
                            `${resourceNames[k] ?? k} ${Math.round(v * 100)}%`
                        )
                        .join(", ")}
                    </p>
                  ) : null}
                  {Object.keys(mine.inventory).length > 0 ? (
                    <p className="text-[12px] text-zinc-400 dark:text-cyan-500/70">
                      Stored:{" "}
                      {Object.entries(mine.inventory)
                        .map(
                          ([k, v]) =>
                            `${resourceNames[k] ?? k}: ${v.toFixed(1)}t`
                        )
                        .join(" · ")}
                    </p>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => handleVisitMine(mine.location ?? "")}
                    className="mt-1 inline-block text-[12px] text-zinc-600 underline hover:text-zinc-800 dark:text-cyan-400 dark:hover:text-cyan-300"
                  >
                    Visit mine →
                  </button>
                </li>
              ))}
            </ul>
              </div>
            </details>
          </section>
        </>
      ) : null}

      {data.character && data.properties && data.properties.length > 0 ? (
        <>
          <SectionDivider />
          <section className="mx-2 rounded-lg border border-rose-200/60 bg-rose-50/50 px-3 py-2 dark:border-rose-800/40 dark:bg-rose-950/20">
            <details className="group">
              <summary className="section-label flex cursor-pointer list-none items-center justify-between [&::-webkit-details-marker]:hidden">
                <span>My Properties</span>
                <svg
                  className="size-3 shrink-0 transition-transform group-open:rotate-90"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </summary>
              <div className="mt-1">
                <ul className="space-y-1">
                  {data.properties.map((p, i) => (
                    <li
                      key={p.claimId}
                      className={`rounded py-1.5 px-2 -mx-2 ${
                        i % 2 === 0 ? "bg-rose-100/40 dark:bg-rose-950/30" : "bg-white/50 dark:bg-rose-900/10"
                      }`}
                    >
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">{p.claimKey}</span>
                        <span className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-[11px] text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                          Tier {p.tier}
                        </span>
                        <span className="rounded bg-violet-100 px-1.5 py-0.5 font-mono text-[11px] text-violet-800 dark:bg-violet-900/40 dark:text-violet-300">
                          {PROPERTY_ZONE_LABEL[p.zone] ?? p.zone}
                        </span>
                      </div>
                      <p className="mt-0.5 text-[12px] text-zinc-500 dark:text-cyan-500/80">
                        {p.lotKey || "—"}
                        {p.referenceListPriceCr != null ? (
                          <>
                            {" "}
                            · ref.{" "}
                            <span className="font-mono tabular-nums text-amber-700 dark:text-amber-400">
                              {p.referenceListPriceCr.toLocaleString()} cr
                            </span>
                          </>
                        ) : null}
                      </p>
                      <Link
                        href={`/properties/${p.claimId}`}
                        className="mt-1 inline-block text-[12px] text-zinc-600 underline hover:text-zinc-800 dark:text-cyan-400 dark:hover:text-cyan-300"
                      >
                        Deed details →
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </details>
          </section>
        </>
      ) : null}
    </main>
  );
}
