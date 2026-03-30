"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { groupExits } from "@/components/exit-grid";
import { PanelExpandButton } from "@/components/panel-expand-button";
import type { ControlSurfaceNav, CsCharacter, NavKiosk } from "@/lib/control-surface-api";
import { formatCr as cr } from "@/lib/format-units";
import { playTravel, type ExitButton } from "@/lib/ui-api";

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
      <div className="flex items-center bg-cyan-900/30 px-1.5 py-0.5 text-xs font-bold uppercase tracking-widest">
        <span className="text-cyber-cyan">{title}</span>
        <PanelExpandButton
          open={open}
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          className="ml-auto shrink-0"
        />
      </div>
      {open ? <div className="border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-xs">{children}</div> : null}
    </section>
  );
}

function Kv({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex min-w-0 gap-1">
      <span className="shrink-0 text-ui-muted">{k}</span>
      <span className="min-w-0 truncate font-mono text-foreground">{v}</span>
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
      className="shrink-0 rounded border border-cyan-800/60 px-1 py-0 text-xs text-cyber-cyan hover:bg-cyan-900/40"
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
      className="font-mono tabular-nums tracking-wide text-cyber-cyan"
      title="Coordinated Universal Time"
    >
      <div className="text-xs leading-tight text-cyber-cyan">{dateStr}</div>
      <div className="text-xs leading-tight">
        {line} UTC
      </div>
    </div>
  );
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
  miningLocalRawStoredValue,
  propertyRefValue,
}: {
  char: CsCharacter;
  morality: Morality;
  miningValuePerCycle: number;
  miningStoredValue: number;
  miningLocalRawStoredValue: number;
  propertyRefValue: number;
}) {
  const hp = char.vitals?.hp;
  const abilityRows = Object.entries(char.abilities || {}).sort(([a], [b]) => a.localeCompare(b));

  return (
    <Panel panelKey="character" title="Character">
      <Row>
        <span className="font-bold text-foreground">{char.key}</span>
      </Row>
      <Kv k="room" v={char.room ?? "—"} />
      <Kv
        k="level"
        v={
          char.level != null && char.xpToNext != null
            ? `Lv ${char.level} · XP ${char.xpIntoLevel ?? 0} / ${char.xpToNext}`
            : "—"
        }
      />
      <Kv k="credits" v={cr(char.credits)} />
      <Kv k="mine yld/cycle" v={cr(miningValuePerCycle)} />
      <Kv k="mine storage" v={cr(miningStoredValue)} />
      <Kv k="local storage" v={cr(miningLocalRawStoredValue)} />
      <Kv k="prop val" v={cr(propertyRefValue)} />
      {hp && <Kv k="hp" v={`${hp.current} / ${hp.max ?? "?"} · AC ${char.armorClass}`} />}
      <div className="mt-0.5 flex flex-wrap gap-x-2 gap-y-0.5">
        {abilityRows.map(([key, ability]) => (
          <span key={key} className="text-ui-muted">
            {key.toUpperCase()} <span className="text-foreground">{ability.score}</span>
          </span>
        ))}
      </div>
      <div className="mt-0.5 flex gap-3 text-xs text-ui-muted">
        <span>
          G <span className="text-foreground">{morality.good}</span>
        </span>
        <span>
          E <span className="text-foreground">{morality.evil}</span>
        </span>
        <span>
          L <span className="text-foreground">{morality.lawful}</span>
        </span>
        <span>
          C <span className="text-foreground">{morality.chaotic}</span>
        </span>
      </div>
    </Panel>
  );
}

function NavDestinationRow({
  exit,
  busyKey,
  onTravel,
}: {
  exit: ExitButton & { destination: string };
  busyKey: string | null;
  onTravel: (destination: string) => void;
}) {
  const k = `exit:${exit.destination}`;
  return (
    <button
      type="button"
      onClick={() => onTravel(exit.destination)}
      disabled={busyKey === k}
      className="block w-full truncate rounded border border-cyan-800/60 px-1 py-0.5 text-left text-xs text-cyber-cyan hover:bg-cyan-900/40 disabled:opacity-40"
    >
      {busyKey === k ? "Moving…" : exit.label}
    </button>
  );
}

function NavPanel({
  nav,
  roomExits,
  onTravelComplete,
}: {
  nav: ControlSurfaceNav;
  roomExits: ExitButton[];
  onTravelComplete: () => void;
}) {
  const router = useRouter();
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const travelLock = useRef(false);
  const kiosks = mergeNavKiosks(nav.kiosks);

  const filteredDestinations = useMemo(
    () => roomExits.filter((e): e is ExitButton & { destination: string } => Boolean(e.destination)),
    [roomExits],
  );

  const destinationGroups = useMemo(() => groupExits(filteredDestinations), [filteredDestinations]);

  const handleExitTravel = useCallback(
    async (destination: string) => {
      if (travelLock.current) return;
      travelLock.current = true;
      const k = `exit:${destination}`;
      setBusyKey(k);
      try {
        await playTravel({ destination });
        router.push("/");
        router.refresh();
        onTravelComplete();
      } finally {
        travelLock.current = false;
        setBusyKey(null);
      }
    },
    [onTravelComplete, router],
  );

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
      {filteredDestinations.length > 0 && (
        <Panel panelKey="hub-exits" title="Destinations">
          {destinationGroups.length <= 1 &&
          (destinationGroups[0]?.title === "Destinations" || !destinationGroups[0]) ? (
            <div className="space-y-0.5">
              {filteredDestinations.map((ex) => (
                <NavDestinationRow key={`${ex.key}-${ex.destination}`} exit={ex} busyKey={busyKey} onTravel={handleExitTravel} />
              ))}
            </div>
          ) : (
            <div className="space-y-1.5">
              {destinationGroups.map(({ title, items }) => (
                <div key={title}>
                  <div className="mb-0.5 text-ui-caption font-semibold uppercase tracking-wide text-ui-muted">{title}</div>
                  <div className="space-y-0.5">
                    {items.map((ex) => (
                      <NavDestinationRow
                        key={`${ex.key}-${ex.destination}`}
                        exit={ex as ExitButton & { destination: string }}
                        busyKey={busyKey}
                        onTravel={handleExitTravel}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
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
              className="block w-full rounded border border-cyan-900/50 bg-zinc-950/80 px-1.5 py-0.5 text-left text-xs uppercase tracking-widest text-cyber-cyan hover:border-cyan-700/60 hover:bg-cyan-950/40 disabled:opacity-50"
            >
              {switchBusy ? "Switching..." : "Switch Character"}
            </button>
          </div>
          <PlayerPanel
            char={data.character}
            morality={data.missions?.morality ?? { good: 0, evil: 0, lawful: 0, chaotic: 0 }}
            miningValuePerCycle={data.productionEstimatedValuePerCycle ?? data.miningEstimatedValuePerCycle ?? 0}
            miningStoredValue={data.productionTotalStoredValue ?? data.miningTotalStoredValue ?? 0}
            miningLocalRawStoredValue={data.miningLocalRawStoredValue ?? 0}
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
              <p className="text-xs font-bold uppercase tracking-widest text-cyber-cyan">Character</p>
              {rows.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  disabled={pickBusy}
                  onClick={() => onPickCharacter(c.id)}
                  className="block w-full truncate rounded border border-cyan-900/50 bg-zinc-950/80 px-1.5 py-0.5 text-left text-foreground hover:border-cyan-700/60 hover:bg-cyan-950/40 disabled:opacity-50"
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
          <Link href="/" className="font-bold text-cyber-cyan hover:text-cyber-cyan">
            AURNOM
          </Link>
          <UtcClock />
        </div>
        <Link href="/messages" className="text-xs font-bold uppercase tracking-widest text-cyber-cyan hover:text-cyber-cyan">
          Messages
        </Link>
        {(loading || pickBusy || switchBusy) && <span className="ml-auto text-ui-caption text-ui-muted">…</span>}
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
        roomExits={data?.roomExits ?? []}
        onTravelComplete={reload}
      />
    </aside>
  );
}
