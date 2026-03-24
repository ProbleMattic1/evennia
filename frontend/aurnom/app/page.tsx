"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

import { getDashboardState, getResources, mineDeploy } from "@/lib/ui-api";
import type { ResourceEntry } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

const EVENNIA_ORIGIN = process.env.NEXT_PUBLIC_EVENNIA_ORIGIN ?? "";

const ABILITY_ORDER = ["str", "dex", "con", "int", "wis", "cha"] as const;

function resourceNameByKey(resources: ResourceEntry[]): Record<string, string> {
  return Object.fromEntries(resources.map((r) => [r.key, r.name]));
}

export default function Home() {
  const loader = useCallback(() => getDashboardState(), []);
  const { data, error, loading, reload } = useUiResource(loader);

  const resourcesLoader = useCallback(() => getResources(), []);
  const { data: resourcesData } = useUiResource(resourcesLoader);

  const [deployPackageId, setDeployPackageId] = useState<number | null>(null);
  const [deployClaimId, setDeployClaimId] = useState<number | null>(null);
  const [deployBusy, setDeployBusy] = useState(false);
  const [deployError, setDeployError] = useState<string | null>(null);
  const [deploySuccess, setDeploySuccess] = useState<string | null>(null);

  const packages = useMemo(
    () => (data?.inventory ?? []).filter((i) => i.isMiningPackage),
    [data?.inventory]
  );
  const claims = useMemo(
    () => (data?.inventory ?? []).filter((i) => i.isMiningClaim),
    [data?.inventory]
  );
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

  const resourceNames = useMemo(
    () => (resourcesData?.resources ? resourceNameByKey(resourcesData.resources) : {}),
    [resourcesData]
  );

  function SectionDivider() {
    return <hr className="section-divider" aria-hidden />;
  }

  if (loading) {
    return (
      <main className="main-content">
        <p className="text-sm text-zinc-500">Loading dashboard…</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="main-content">
        <p className="text-sm text-red-600">Failed to load dashboard: {error ?? "Unknown error"}</p>
      </main>
    );
  }

  return (
    <main className="main-content">
      <header className="border-b border-zinc-200 py-3">
        <div className="px-2">
          <h1 className="text-base font-semibold text-zinc-900">Aurnom</h1>
          <p className="mt-0.5 text-[12px] text-zinc-500">
            {data.character
              ? `Signed in as ${data.character.key}. Location: ${data.character.room ?? "Unknown"}.`
              : "Character dashboard and entry point for the Evennia-powered world."}
          </p>
        </div>
        {data.character && data.credits !== null ? (
          <dl className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 border-t border-zinc-200 px-2 pt-2">
            <div className="flex min-w-0 flex-col gap-0">
              <dt className="text-[12px] font-medium uppercase tracking-wide text-zinc-400">
                Credits
              </dt>
              <dd className="font-mono text-sm tabular-nums text-zinc-700">
                {data.credits.toLocaleString()} <span className="text-zinc-400">cr</span>
              </dd>
            </div>
            {(data.miningEstimatedValuePerCycle ?? 0) > 0 ||
            (data.miningTotalStoredValue ?? 0) > 0 ? (
              <>
                <div className="flex min-w-0 flex-col gap-0">
                  <dt className="text-[12px] font-medium uppercase tracking-wide text-zinc-400">
                    Est. value / cycle
                  </dt>
                  <dd className="font-mono text-sm tabular-nums text-zinc-700">
                    {(data.miningEstimatedValuePerCycle ?? 0).toLocaleString()}{" "}
                    <span className="text-zinc-400">cr</span>
                  </dd>
                </div>
                <div className="flex min-w-0 flex-col gap-0">
                  <dt className="text-[12px] font-medium uppercase tracking-wide text-zinc-400">
                    Stored value
                  </dt>
                  <dd className="font-mono text-sm tabular-nums text-zinc-700">
                    {(data.miningTotalStoredValue ?? 0).toLocaleString()}{" "}
                    <span className="text-zinc-400">cr</span>
                  </dd>
                </div>
              </>
            ) : null}
            <div className="flex min-w-0 flex-col gap-0">
              <dt className="text-[12px] font-medium uppercase tracking-wide text-zinc-400">
                Armor class
              </dt>
              <dd className="font-mono text-sm tabular-nums text-zinc-700">
                {data.character.armorClass}
              </dd>
            </div>
            {data.character.vitals.hp ? (
              <div className="flex min-w-0 flex-col gap-0">
                <dt className="text-[12px] font-medium uppercase tracking-wide text-zinc-400">
                  {data.character.vitals.hp.name}
                </dt>
                <dd className="font-mono text-sm tabular-nums text-zinc-700">
                  {data.character.vitals.hp.current}
                  {data.character.vitals.hp.max != null ? (
                    <>
                      {" "}
                      <span className="text-zinc-400">/ {data.character.vitals.hp.max}</span>
                    </>
                  ) : null}
                </dd>
              </div>
            ) : null}
          </dl>
        ) : null}
        {data.character ? (
          <div className="mt-2 border-t border-zinc-200 px-2 pt-2">
            <p className="mb-1.5 section-label">Ability scores</p>
            <div className="flex flex-wrap gap-x-3 gap-y-1">
              {ABILITY_ORDER.map((key) => {
                const row = data.character!.abilities[key];
                if (!row) return null;
                const label = key.toUpperCase();
                return (
                  <span
                    key={key}
                    className="inline-flex items-baseline gap-1.5 text-[12px] text-zinc-600"
                  >
                    <span className="font-semibold text-zinc-500">{label}</span>
                    <span className="font-mono tabular-nums text-zinc-800">{row.score}</span>
                    <span className="text-zinc-400">
                      ({row.name}, Mod {row.abilityMod >= 0 ? "+" : ""}
                      {row.abilityMod})
                    </span>
                  </span>
                );
              })}
            </div>
          </div>
        ) : null}
      </header>

      {!data.authenticated ? (
        <p className="mx-2 mt-2 rounded border border-amber-200/60 bg-amber-50/80 px-2 py-1.5 text-[12px] text-amber-800">
          Sign in on the game server with the same browser session to see your character, credits, and
          inventory here.
          {EVENNIA_ORIGIN ? (
            <>
              {" "}
              <a href={`${EVENNIA_ORIGIN.replace(/\/$/, "")}/`} className="font-medium underline">
                Open game site
              </a>
            </>
          ) : null}
        </p>
      ) : null}

      {data.authenticated && data.message ? (
        <p className="mx-2 mt-2 rounded border border-amber-200/60 bg-amber-50/80 px-2 py-1.5 text-[12px] text-amber-800">
          {data.message}
        </p>
      ) : null}

      {data.character ? (
        <>
          <SectionDivider />
          <section className="px-2 py-2">
            <h2 className="section-label">Inventory</h2>
            {data.inventory.length === 0 ? (
              <p className="mt-1 text-sm text-zinc-500">You are not carrying any items.</p>
            ) : (
              <ul className="mt-1 space-y-0.5">
                {data.inventory.map((item) => (
                  <li
                    key={item.id}
                    className="border-b border-zinc-100 py-1.5 last:border-0"
                  >
                    <div className="flex justify-between gap-2">
                      <span className="truncate text-sm font-medium text-zinc-800">{item.key}</span>
                      {item.description ? (
                        <span className="max-w-[12rem] shrink-0 truncate text-[12px] text-zinc-500">
                          {item.description}
                        </span>
                      ) : null}
                    </div>
                    {item.isMiningClaim && item.claimSpecs ? (
                      <div className="mt-1 space-y-0.5">
                        <p className="text-[12px] text-zinc-500">
                          {item.claimSpecs.roomKey} · Richness{" "}
                          {Math.round(item.claimSpecs.richness * 100)}% ·{" "}
                          {item.claimSpecs.baseOutputTons}t/cycle · Hazard{" "}
                          {item.claimSpecs.hazardLabel}
                        </p>
                        {Object.keys(item.claimSpecs.composition).length > 0 ? (
                          <p className="text-[12px] text-zinc-500">
                            {Object.entries(item.claimSpecs.composition)
                              .map(
                                ([k, v]) =>
                                  `${resourceNames[k] ?? k} ${Math.round(v * 100)}%`
                              )
                              .join(", ")}
                          </p>
                        ) : null}
                        <p className="text-[12px] font-medium text-zinc-600">
                          Est. ~
                          {item.claimSpecs.estimatedValuePerCycle.toLocaleString()} cr/cycle
                        </p>
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}

      {data.character && canDeploy ? (
        <>
          <SectionDivider />
          <section className="px-2 py-2">
            <h2 className="section-label">Deploy Mine</h2>
            <p className="mt-1 text-[12px] text-zinc-500">
              Choose a package and claim to deploy a mining operation.
            </p>
            <div className="mt-2 flex flex-wrap gap-3">
              <div>
                <label className="block text-[12px] font-medium text-zinc-500">Package</label>
                <select
                  className="mt-0.5 rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-800"
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
                <label className="block text-[12px] font-medium text-zinc-500">Claim</label>
                <select
                  className="mt-0.5 rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-800"
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
                  className="rounded bg-zinc-800 px-3 py-1 text-sm text-white hover:bg-zinc-700 disabled:opacity-50"
                  disabled={deployBusy || deployPackageId == null || deployClaimId == null}
                  onClick={handleDeploy}
                >
                  {deployBusy ? "Deploying…" : "Deploy"}
                </button>
              </div>
            </div>
            {deployError ? (
              <p className="mt-2 text-[12px] text-red-600">{deployError}</p>
            ) : null}
            {deploySuccess ? (
              <p className="mt-2 text-[12px] text-emerald-600">{deploySuccess}</p>
            ) : null}
          </section>
        </>
      ) : null}

      {data.character ? (
        <>
          <SectionDivider />
          <section className="px-2 py-2">
            <h2 className="section-label">Ships</h2>
            {data.ships.length === 0 ? (
              <p className="mt-1 text-sm text-zinc-500">
                No owned ships yet. Visit the{" "}
                <Link
                  href="/shop?room=Meridian%20Civil%20Shipyard"
                  className="text-zinc-700 underline hover:text-zinc-900"
                >
                  shipyard
                </Link>{" "}
                to buy one.
              </p>
            ) : (
              <ul className="mt-1 space-y-1">
                {data.ships.map((ship) => (
                  <li
                    key={ship.id}
                    className="border-b border-zinc-100 py-1.5 last:border-0"
                  >
                    <span className="text-sm font-medium text-zinc-800">{ship.key}</span>
                    <span className="ml-2 text-[12px] text-zinc-500">{ship.summary}</span>
                    <p className="mt-0.5 text-[12px] text-zinc-400">
                      {ship.location ?? "—"} · {ship.state ?? "—"} · {ship.pilot ?? "—"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}

      {data.character && data.mines && data.mines.length > 0 ? (
        <>
          <SectionDivider />
          <section className="px-2 py-2">
            <h2 className="section-label">My Mines</h2>
            <ul className="mt-1 space-y-1">
              {data.mines.map((mine) => (
                <li
                  key={mine.key}
                  className="border-b border-zinc-100 py-1.5 last:border-0"
                >
                  <span className="text-sm font-medium text-zinc-800">{mine.key}</span>
                  <span className="ml-2 text-[12px] text-zinc-500">
                    {mine.location ?? "—"} · {mine.active ? "Active" : "Inactive"}
                  </span>
                  <p className="mt-0.5 text-[12px] text-zinc-400">
                    Storage: {mine.storageUsed}/{mine.storageCapacity}t
                    {mine.nextCycleAt
                      ? ` · Next: ${new Date(mine.nextCycleAt).toLocaleString()}`
                      : ""}
                  </p>
                  {mine.rig ? (
                    <p className="text-[12px] text-zinc-400">
                      Rig: {mine.rig} ({mine.rigWear ?? 0}% wear)
                    </p>
                  ) : null}
                  {Object.keys(mine.composition).length > 0 ? (
                    <p className="text-[12px] text-zinc-400">
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
                    <p className="text-[12px] text-zinc-400">
                      Stored:{" "}
                      {Object.entries(mine.inventory)
                        .map(
                          ([k, v]) =>
                            `${resourceNames[k] ?? k}: ${v.toFixed(1)}t`
                        )
                        .join(" · ")}
                    </p>
                  ) : null}
                  <Link
                    href={`/play?room=${encodeURIComponent(mine.location ?? "")}`}
                    className="mt-1 inline-block text-[12px] text-zinc-600 underline hover:text-zinc-800"
                  >
                    Visit mine →
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </>
      ) : null}
    </main>
  );
}
