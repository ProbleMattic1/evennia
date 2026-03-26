"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import type { ControlSurfaceNav, CsCharacter } from "@/lib/control-surface-api";
import { useControlSurface } from "@/components/control-surface-provider";

function Panel({ title, children, className = "" }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section className={`mb-1 ${className}`}>
      <div className="bg-cyan-900/30 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-cyan-500">
        {title}
      </div>
      <div className="border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-[11px]">{children}</div>
    </section>
  );
}

function Kv({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex min-w-0 gap-1">
      <span className="shrink-0 text-zinc-500">{k}</span>
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

function TinyButton({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="shrink-0 rounded border border-cyan-800/60 px-1 py-0 text-[10px] text-cyan-400 hover:bg-cyan-900/40"
    >
      {children}
    </button>
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
  propertyRefValue,
  onReload,
}: {
  char: CsCharacter;
  morality: Morality;
  miningValuePerCycle: number;
  miningStoredValue: number;
  propertyRefValue: number;
  onReload: () => void;
}) {
  const hp = char.vitals?.hp;
  const abilityRows = Object.entries(char.abilities || {}).sort(([a], [b]) => a.localeCompare(b));

  return (
    <Panel title="Character">
      <Row>
        <span className="font-bold text-zinc-100">{char.key}</span>
        <span className="ml-auto text-zinc-500">AC {char.armorClass}</span>
      </Row>
      <Kv k="room" v={char.room ?? "—"} />
      <Kv k="credits" v={cr(char.credits)} />
      <Kv k="mine yield/cycle" v={cr(miningValuePerCycle)} />
      <Kv k="ore stored" v={cr(miningStoredValue)} />
      <Kv k="property ref val" v={cr(propertyRefValue)} />
      {hp && <Kv k="hp" v={`${hp.current} / ${hp.max ?? "?"}`} />}
      <div className="mt-0.5 flex flex-wrap gap-x-2 gap-y-0.5">
        {abilityRows.map(([key, ability]) => (
          <span key={key} className="text-zinc-500">
            {key.toUpperCase()} <span className="text-zinc-200">{ability.score}</span>
          </span>
        ))}
      </div>
      <div className="mt-0.5 flex gap-3 text-[10px] text-zinc-500">
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
      <div className="mt-1">
        <TinyButton onClick={onReload}>Refresh</TinyButton>
      </div>
    </Panel>
  );
}

function NavPanel({ nav }: { nav: ControlSurfaceNav }) {
  return (
    <>
      {nav.kiosks.length > 0 && (
        <Panel title="Services">
          {nav.kiosks.map((k) => (
            <div key={k.key}>
              <TinyLink href={k.href}>{k.label}</TinyLink>
            </div>
          ))}
        </Panel>
      )}
      {nav.shops.length > 0 && (
        <Panel title="Shops">
          {nav.shops.map((s) => (
            <div key={s.roomKey}>
              <TinyLink href={`/shop?room=${encodeURIComponent(s.roomKey)}`}>{s.label}</TinyLink>
            </div>
          ))}
        </Panel>
      )}
      {nav.claims.length > 0 && (
        <Panel title="Claims">
          {nav.claims.map((c) => (
            <div key={c.href}>
              <TinyLink href={c.href}>{c.label}</TinyLink>
            </div>
          ))}
        </Panel>
      )}
      {nav.properties.length > 0 && (
        <Panel title="Property Deeds">
          {nav.properties.map((p) => (
            <div key={p.href}>
              <TinyLink href={p.href}>{p.label}</TinyLink>
            </div>
          ))}
        </Panel>
      )}
      {nav.mines.length > 0 && (
        <Panel title="Mines">
          {nav.mines.map((m) => (
            <Row key={m.href}>
              <TinyLink href={m.href}>{m.label}</TinyLink>
              {m.active && <span className="text-[9px] text-green-400">●</span>}
            </Row>
          ))}
        </Panel>
      )}
      {nav.exits.length > 0 && (
        <Panel title="Hub Exits">
          {nav.exits.map((e) => (
            <div key={e.key} className="text-zinc-400">
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

  return (
    <aside className="sticky top-0 h-svh min-w-0 overflow-y-auto border-r border-cyan-900/40 p-1.5">
      <div className="mb-1 flex items-center gap-1 border-b border-cyan-900/40 pb-1">
        <Link href="/" className="font-bold text-cyan-400 hover:text-cyan-300">
          AURNOM
        </Link>
        {loading && <span className="ml-auto text-[9px] text-zinc-500">…</span>}
      </div>

      {!data && error ? <div className="mb-1 text-red-400">{error}</div> : null}

      {data?.character ? (
        <PlayerPanel
          char={data.character}
          morality={data.missions?.morality ?? { good: 0, evil: 0, lawful: 0, chaotic: 0 }}
          miningValuePerCycle={data.miningEstimatedValuePerCycle ?? 0}
          miningStoredValue={data.miningTotalStoredValue ?? 0}
          propertyRefValue={data.propertyReferenceListValueTotalCr ?? 0}
          onReload={reload}
        />
      ) : (
        <div className="text-zinc-600">Not logged in.</div>
      )}

      <NavPanel nav={data?.nav ?? { hubRoomKey: "", exits: [], kiosks: [], shops: [], claims: [], properties: [], mines: [] }} />
    </aside>
  );
}
