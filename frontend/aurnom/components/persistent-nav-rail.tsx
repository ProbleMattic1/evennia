"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import type { ControlSurfaceNav, CsCharacter, NavKiosk } from "@/lib/control-surface-api";

/** Web routes not guaranteed on older API payloads; append after server kiosks. */
const WEB_ONLY_KIOSKS: NavKiosk[] = [{ key: "economy", label: "Economy", href: "/economy" }];

function mergeNavKiosks(kiosks: NavKiosk[]): NavKiosk[] {
  const seen = new Set(kiosks.map((k) => k.href));
  const out = [...kiosks];
  for (const k of WEB_ONLY_KIOSKS) {
    if (!seen.has(k.href)) {
      out.push(k);
      seen.add(k.href);
    }
  }
  return out;
}
import { clearWebActiveCharacter, setWebActiveCharacter } from "@/lib/control-surface-api";
import { useControlSurface } from "@/components/control-surface-provider";

function Panel({
  panelKey,
  title,
  children,
  className = "",
}: {
  panelKey: string;
  title: string;
  children: ReactNode;
  className?: string;
}) {
  const storageKey = `aurnom:nav-panel:${panelKey}`;
  const [open, setOpen] = useState(() => {
    if (typeof window === "undefined") return true;
    try {
      const raw = window.sessionStorage.getItem(storageKey);
      return raw == null ? true : raw === "1";
    } catch {
      return true;
    }
  });

  useEffect(() => {
    try {
      window.sessionStorage.setItem(storageKey, open ? "1" : "0");
    } catch {
      // ignore storage errors and keep UI functional
    }
  }, [open, storageKey]);

  return (
    <section className={`mb-1 ${className}`}>
      <div className="flex items-center bg-cyan-900/30 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-cyan-300">
        <span>{title}</span>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          className="ml-auto px-1 text-cyan-400 hover:text-cyan-300"
        >
          {open ? "▴" : "▸"}
        </button>
      </div>
      {open ? <div className="border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-[11px]">{children}</div> : null}
    </section>
  );
}

function Kv({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex min-w-0 gap-1">
      <span className="shrink-0 text-ui-muted">{k}</span>
      <span className="min-w-0 truncate font-mono text-zinc-200">{v}</span>
    </div>
  );
}

function Row({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`flex min-w-0 items-baseline gap-2 ${className}`}>{children}</div>;
}

function TinyLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="shrink-0 rounded border border-cyan-800/60 px-1 py-0 text-[10px] text-cyan-400 hover:bg-cyan-900/40"
    >
      {children}
    </Link>
  );
}

function UtcClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);
  const dateStr = now.toLocaleDateString("en-GB", {
    timeZone: "UTC",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  const line = now.toLocaleTimeString("en-GB", {
    timeZone: "UTC",
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  return (
    <div
      className="font-mono tabular-nums tracking-wide text-cyan-300"
      title="Coordinated Universal Time"
    >
      <div className="text-[10px] leading-tight text-cyan-300">{dateStr}</div>
      <div className="text-[11px] leading-tight">
        {line} UTC
      </div>
    </div>
  );
}

function cr(n: number | null | undefined) {
  if (n == null) return "—";
  return `${n.toLocaleString()} cr`;
}

type Morality = {
  good: number;
  evil: number;
  lawful: number;
  chaotic: number;
};

function PlayerPanel({
  char,
  morality,
  miningValuePerCycle,
  miningStoredValue,
  miningPersonalStoredValue,
  propertyRefValue,
}: {
  char: CsCharacter;
  morality: Morality;
  miningValuePerCycle: number;
  miningStoredValue: number;
  miningPersonalStoredValue: number;
  propertyRefValue: number;
}) {
  const hp = char.vitals?.hp;
  const abilityRows = Object.entries(char.abilities || {}).sort(([a], [b]) => a.localeCompare(b));

  return (
    <Panel panelKey="character" title="Character">
      <Row>
        <span className="font-bold text-zinc-100">{char.key}</span>
      </Row>
      <Kv k="room" v={char.room ?? "—"} />
      <Kv k="credits" v={cr(char.credits)} />
      <Kv k="mine yld/cycle" v={cr(miningValuePerCycle)} />
      <Kv k="mine storage" v={cr(miningStoredValue)} />
      <Kv k="local storage" v={cr(miningPersonalStoredValue)} />
      <Kv k="prop val" v={cr(propertyRefValue)} />
      {hp && <Kv k="hp" v={`${hp.current} / ${hp.max ?? "?"} · AC ${char.armorClass}`} />}
      <div className="mt-0.5 flex flex-wrap gap-x-2 gap-y-0.5">
        {abilityRows.map(([key, ability]) => (
          <span key={key} className="text-ui-muted">
            {key.toUpperCase()} <span className="text-zinc-200">{ability.score}</span>
          </span>
        ))}
      </div>
      <div className="mt-0.5 flex gap-3 text-[10px] text-ui-muted">
        <span>
          G <span className="text-zinc-300">{morality.good}</span>
        </span>
        <span>
          E <span className="text-zinc-300">{morality.evil}</span>
        </span>
        <span>
          L <span className="text-zinc-300">{morality.lawful}</span>
        </span>
        <span>
          C <span className="text-zinc-300">{morality.chaotic}</span>
        </span>
      </div>
    </Panel>
  );
}

function NavPanel({ nav }: { nav: ControlSurfaceNav }) {
  const kiosks = mergeNavKiosks(nav.kiosks);
  return (
    <>
      {kiosks.length > 0 && (
        <Panel panelKey="services" title="Services">
          {kiosks.map((k) => (
            <div key={k.href}>
              <TinyLink href={k.href}>{k.label}</TinyLink>
            </div>
          ))}
        </Panel>
      )}
      {nav.shops.length > 0 && (
        <Panel panelKey="shops" title="Shops">
          {nav.shops.map((s) => (
            <div key={s.roomKey}>
              <TinyLink href={`/shop?room=${encodeURIComponent(s.roomKey)}`}>{s.label}</TinyLink>
            </div>
          ))}
        </Panel>
      )}
      {nav.exits.length > 0 && (
        <Panel panelKey="hub-exits" title="Destinations">
          {nav.exits.map((e) => (
            <div key={e.key} className="text-ui-muted">
              {e.label}
            </div>
          ))}
        </Panel>
      )}
    </>
  );
}

export function PersistentNavRail() {
  const { data, loading, error, reload } = useControlSurface();
  const [pickBusy, setPickBusy] = useState(false);
  const [pickErr, setPickErr] = useState<string | null>(null);
  const [switchBusy, setSwitchBusy] = useState(false);

  const onPickCharacter = useCallback(
    async (characterId: number) => {
      setPickErr(null);
      setPickBusy(true);
      try {
        await setWebActiveCharacter(characterId);
        reload();
      } catch (e) {
        setPickErr(e instanceof Error ? e.message : "Could not set character.");
      } finally {
        setPickBusy(false);
      }
    },
    [reload],
  );

  const onSwitchCharacter = useCallback(async () => {
    setPickErr(null);
    setSwitchBusy(true);
    try {
      await clearWebActiveCharacter();
      reload();
    } catch (e) {
      setPickErr(e instanceof Error ? e.message : "Could not switch character.");
    } finally {
      setSwitchBusy(false);
    }
  }, [reload]);

  const railBody = (() => {
    if (data?.character) {
      return (
        <>
          <div className="mb-1">
            <button
              type="button"
              disabled={switchBusy}
              onClick={onSwitchCharacter}
              className="block w-full rounded border border-cyan-900/50 bg-zinc-950/80 px-1.5 py-0.5 text-left text-[10px] uppercase tracking-widest text-cyan-300 hover:border-cyan-700/60 hover:bg-cyan-950/40 disabled:opacity-50"
            >
              {switchBusy ? "Switching..." : "Switch Character"}
            </button>
          </div>
          <PlayerPanel
            char={data.character}
            morality={data.missions?.morality ?? { good: 0, evil: 0, lawful: 0, chaotic: 0 }}
            miningValuePerCycle={data.productionEstimatedValuePerCycle ?? data.miningEstimatedValuePerCycle ?? 0}
            miningStoredValue={data.productionTotalStoredValue ?? data.miningTotalStoredValue ?? 0}
            miningPersonalStoredValue={data.miningPersonalStoredValue ?? 0}
            propertyRefValue={data.propertyReferenceListValueTotalCr ?? 0}
          />
        </>
      );
    }
    if (data?.authenticated) {
      const rows = data.playableCharacters ?? [];
      return (
        <div className="space-y-1 text-ui-muted">
          {data.message ? <p className="text-amber-200">{data.message}</p> : null}
          {pickErr ? <p className="text-red-400">{pickErr}</p> : null}
          {rows.length > 0 ? (
            <div className="space-y-0.5">
              <p className="text-[10px] font-bold uppercase tracking-widest text-cyan-600">Character</p>
              {rows.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  disabled={pickBusy}
                  onClick={() => onPickCharacter(c.id)}
                  className="block w-full truncate rounded border border-cyan-900/50 bg-zinc-950/80 px-1.5 py-0.5 text-left text-zinc-200 hover:border-cyan-700/60 hover:bg-cyan-950/40 disabled:opacity-50"
                >
                  {c.key}
                </button>
              ))}
            </div>
          ) : (
            <p className="text-ui-muted">No playable character on this account.</p>
          )}
        </div>
      );
    }
    return <div className="text-ui-muted">Not logged in.</div>;
  })();

  return (
    <aside className="sticky top-0 h-svh min-w-0 overflow-y-auto border-r border-cyan-900/40 p-1.5">
      <div className="mb-1 flex flex-wrap items-start gap-x-2 gap-y-0.5 border-b border-cyan-900/40 pb-1">
        <div className="flex min-w-0 flex-col leading-tight">
          <Link href="/" className="font-bold text-cyan-400 hover:text-cyan-300">
            AURNOM
          </Link>
          <UtcClock />
        </div>
        <Link href="/messages" className="text-[10px] font-bold uppercase tracking-widest text-cyan-300 hover:text-cyan-300">
          Messages
        </Link>
        {(loading || pickBusy || switchBusy) && <span className="ml-auto text-[9px] text-ui-muted">…</span>}
      </div>

      {!data && error ? <div className="mb-1 text-red-400">{error}</div> : null}

      {railBody}

      <NavPanel
        nav={
          data?.nav ?? {
            hubRoomKey: "",
            exits: [],
            kiosks: [],
            shops: [],
            claims: [],
            properties: [],
            resources: [],
            mines: [],
          }
        }
      />
    </aside>
  );
}
