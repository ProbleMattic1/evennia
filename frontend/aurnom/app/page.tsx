"use client";

import { useCallback } from "react";

import { getDashboardState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

const EVENNIA_ORIGIN = process.env.NEXT_PUBLIC_EVENNIA_ORIGIN ?? "";

const ABILITY_ORDER = ["str", "dex", "con", "int", "wis", "cha"] as const;

export default function Home() {
  const loader = useCallback(() => getDashboardState(), []);
  const { data, error, loading } = useUiResource(loader);

  if (loading) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-10">
        <p className="text-zinc-600">Loading dashboard…</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-10">
        <p className="text-red-600">Failed to load dashboard: {error ?? "Unknown error"}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-10">
      <header className="relative isolate overflow-hidden rounded-2xl border border-white/5 p-6 text-white ring-1 ring-inset ring-white/10">
        <div className="pointer-events-none absolute inset-0 bg-zinc-950" aria-hidden />
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_20%_-20%,rgba(99,102,241,0.25),transparent_50%)]"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_100%_0%,rgba(56,189,248,0.12),transparent_45%)]"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-0 bg-gradient-to-br from-violet-950/40 via-zinc-950 to-black"
          aria-hidden
        />
        <div className="dashboard-space-nebula-drift pointer-events-none absolute inset-0" aria-hidden />
        <div className="dashboard-space-stars pointer-events-none absolute inset-0" aria-hidden />
        <div className="relative z-10">
        <h1 className="text-3xl font-bold">Aurnom</h1>
        <p className="mt-3 max-w-2xl text-sm text-zinc-300">
          {data.character
            ? `Signed in as ${data.character.key}. Location: ${data.character.room ?? "Unknown"}.`
            : "Character dashboard and entry point for the Evennia-powered world."}
        </p>
        {data.character && data.credits !== null ? (
          <dl className="mt-4 flex flex-wrap items-baseline gap-x-6 gap-y-2 border-t border-white/10 pt-4">
            <div className="flex min-w-0 flex-col gap-0.5">
              <dt className="text-[10px] font-medium uppercase tracking-wide text-zinc-500">
                Credits
              </dt>
              <dd className="font-mono text-sm font-semibold tabular-nums tracking-tight text-zinc-100">
                {data.credits.toLocaleString()} <span className="text-zinc-500">cr</span>
              </dd>
            </div>
            <div className="flex min-w-0 flex-col gap-0.5">
              <dt className="text-[10px] font-medium uppercase tracking-wide text-zinc-500">
                Armor class
              </dt>
              <dd className="font-mono text-sm font-semibold tabular-nums tracking-tight text-zinc-100">
                {data.character.armorClass}
              </dd>
            </div>
            {data.character.vitals.hp ? (
              <div className="flex min-w-0 flex-col gap-0.5">
                <dt className="text-[10px] font-medium uppercase tracking-wide text-zinc-500">
                  {data.character.vitals.hp.name}
                </dt>
                <dd className="font-mono text-sm font-semibold tabular-nums tracking-tight text-zinc-100">
                  {data.character.vitals.hp.current}
                  {data.character.vitals.hp.max != null ? (
                    <>
                      {" "}
                      <span className="text-zinc-500">/ {data.character.vitals.hp.max}</span>
                    </>
                  ) : null}
                </dd>
              </div>
            ) : null}
          </dl>
        ) : null}
        {data.character ? (
          <div className="mt-4 border-t border-white/10 pt-4">
            <p className="mb-2 text-[10px] font-medium uppercase tracking-wide text-zinc-500">
              Ability scores
            </p>
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
              {ABILITY_ORDER.map((key) => {
                const row = data.character!.abilities[key];
                if (!row) {
                  return null;
                }
                const label = key.toUpperCase();
                return (
                  <div
                    key={key}
                    className="rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                  >
                    <div className="flex items-start justify-between gap-1">
                      <span className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
                        {label}
                      </span>
                      <span className="font-mono text-lg font-semibold tabular-nums text-zinc-100">
                        {row.score}
                      </span>
                    </div>
                    <p className="mt-0.5 truncate text-[10px] text-zinc-400">{row.name}</p>
                    <p className="mt-1 font-mono text-xs text-zinc-300">
                      Mod {row.abilityMod >= 0 ? "+" : ""}
                      {row.abilityMod}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
        </div>
      </header>

      {!data.authenticated ? (
        <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
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
        <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          {data.message}
        </p>
      ) : null}

      {data.character ? (
        <section className="rounded-xl border border-zinc-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-zinc-900">Inventory</h2>
          {data.inventory.length === 0 ? (
            <p className="mt-2 text-sm text-zinc-600">You are not carrying any items.</p>
          ) : (
            <ul className="mt-4 grid gap-3 sm:grid-cols-2">
              {data.inventory.map((item) => (
                <li key={item.id} className="rounded-lg border border-zinc-200 p-4">
                  <h3 className="font-semibold text-zinc-950">{item.key}</h3>
                  {item.description ? (
                    <p className="mt-2 text-sm text-zinc-600">{item.description}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {data.character ? (
        <section className="rounded-xl border border-zinc-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-zinc-900">Ships</h2>
          {data.ships.length === 0 ? (
            <p className="mt-2 text-sm text-zinc-600">
              No owned ships yet. Visit the shipyard to buy one.
            </p>
          ) : (
            <ul className="mt-4 grid gap-4 md:grid-cols-2">
              {data.ships.map((ship) => (
                <li key={ship.id} className="rounded-lg border border-zinc-200 p-4">
                  <h3 className="font-semibold text-zinc-950">{ship.key}</h3>
                  <p className="mt-2 text-sm text-zinc-700">{ship.summary}</p>
                  <dl className="mt-3 grid gap-1 text-xs text-zinc-600">
                    <div>
                      <dt className="inline font-medium">Location:</dt>{" "}
                      <dd className="inline">{ship.location ?? "—"}</dd>
                    </div>
                    <div>
                      <dt className="inline font-medium">State:</dt>{" "}
                      <dd className="inline">{ship.state ?? "—"}</dd>
                    </div>
                    <div>
                      <dt className="inline font-medium">Pilot:</dt>{" "}
                      <dd className="inline">{ship.pilot ?? "—"}</dd>
                    </div>
                  </dl>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}
    </main>
  );
}
