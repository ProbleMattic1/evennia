"use client";

import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { groupExits } from "@/components/exit-grid";
import { NavRailCollapsiblePanel as Panel, NAV_RAIL_DESTINATION_ROW_CLASS } from "@/components/nav-rail-collapsible-panel";
import { PlacesNavPanel } from "@/components/places-nav-panel";
import { PanelExpandButton } from "@/components/panel-expand-button";
import { SortableNavDestinationGroup } from "@/components/sortable-nav-destination-group";
import { SortableNavDestinationRow } from "@/components/sortable-nav-destination-row";
import { useControlSurface } from "@/components/control-surface-provider";
import {
  clearWebActiveCharacter,
  setWebActiveCharacter,
  type CsCharacter,
} from "@/lib/control-surface-api";
import { formatCr as cr } from "@/lib/format-units";
import {
  NAV_RAIL_EXIT_ROW_FLAT_SLUG,
  normalizeExitRowOrder,
  slugifyNavSectionTitle,
} from "@/lib/nav-rail-exit-row-order";
import { useDashboardPanelOpen } from "@/lib/use-dashboard-panel-open";
import { useNavRailDestinationGroupOrder } from "@/lib/use-nav-rail-destination-group-order";
import { useNavRailExitRowOrder } from "@/lib/use-nav-rail-exit-row-order";
import { isPlacesNavContentVisible } from "@/lib/dashboard-right-column-visibility";
import { playTravel, webNavigatePathFromPlayResult, type ExitButton } from "@/lib/ui-api";

function orderedExitKeys(
  sectionSlug: string,
  items: (ExitButton & { destination: string })[],
  bySection: Record<string, string[]>,
  rowOrderHydrated: boolean,
): string[] {
  const current = items.map((ex) => ex.key);
  if (!rowOrderHydrated) return current;
  return normalizeExitRowOrder(bySection[sectionSlug], current);
}

function Kv({ k, v, title }: { k: string; v: ReactNode; title?: string }) {
  return (
    <div className="flex min-w-0 gap-1" title={title}>
      <span className="shrink-0 text-ui-muted">{k}</span>
      <span className="min-w-0 truncate font-mono text-foreground">{v}</span>
    </div>
  );
}

function Row({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`flex min-w-0 items-baseline gap-2 ${className}`}>{children}</div>;
}

function UtcClock() {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect -- clock mounts after hydration; avoids SSR time skew */
    setNow(new Date());
    const id = window.setInterval(() => setNow(new Date()), 1000);
    /* eslint-enable react-hooks/set-state-in-effect */
    return () => window.clearInterval(id);
  }, []);

  if (!now) {
    return (
      <div
        className="font-mono tabular-nums tracking-wide text-cyber-cyan"
        title="Coordinated Universal Time"
      >
        <div className="text-xs leading-tight text-cyber-cyan">…</div>
        <div className="text-xs leading-tight">--:--:-- UTC</div>
      </div>
    );
  }

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
      <div className="text-xs leading-tight">{line} UTC</div>
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
}: {
  char: CsCharacter;
  morality: Morality;
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
      {char.achievements != null ? (
        <Kv
          k="achievements"
          v={`${char.achievements.completed} / ${char.achievements.total}`}
          title="Milestones tracked by the achievements system (completed / defined)."
        />
      ) : null}
      <Kv k="credits" v={cr(char.credits)} />
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
      className={NAV_RAIL_DESTINATION_ROW_CLASS}
    >
      {busyKey === k ? "Moving…" : exit.label}
    </button>
  );
}

function navExitGroupStorageKey(title: string) {
  return `nav-rail:exit-group:${slugifyNavSectionTitle(title)}`;
}

/** Matches SortableNavDestinationGroup: 1.25rem drag track + gap-x-1. Nested list outdent (fraction of that gutter). */
const NAV_SECTION_NESTED_OUTDENT_FRAC = 0.6;
const navSectionNestedOutdentStyles = {
  marginLeft: `calc((1.25rem + 0.25rem) * ${-NAV_SECTION_NESTED_OUTDENT_FRAC})`,
  width: `calc(100% + (1.25rem + 0.25rem) * ${NAV_SECTION_NESTED_OUTDENT_FRAC})`,
} as const;

function NavDestinationGroup({
  title,
  items,
  busyKey,
  onTravel,
  rowOrder,
  rowOrderHydrated,
  onRowDragEnd,
  sensors,
}: {
  title: string;
  items: (ExitButton & { destination: string })[];
  busyKey: string | null;
  onTravel: (destination: string) => void;
  rowOrder: string[];
  rowOrderHydrated: boolean;
  onRowDragEnd: (event: DragEndEvent) => void;
  sensors: ReturnType<typeof useSensors>;
}) {
  const [open, setOpen] = useDashboardPanelOpen(navExitGroupStorageKey(title), true);

  const exitByKey = useMemo(() => {
    const m = new Map<string, ExitButton & { destination: string }>();
    for (const ex of items) m.set(ex.key, ex);
    return m;
  }, [items]);

  const listBody =
    rowOrderHydrated && items.length > 1 ? (
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onRowDragEnd}>
        <SortableContext items={rowOrder} strategy={verticalListSortingStrategy}>
          {rowOrder.map((k) => {
            const ex = exitByKey.get(k);
            if (!ex) return null;
            return (
              <SortableNavDestinationRow key={k} id={k}>
                <NavDestinationRow exit={ex} busyKey={busyKey} onTravel={onTravel} />
              </SortableNavDestinationRow>
            );
          })}
        </SortableContext>
      </DndContext>
    ) : (
      <div className="space-y-0.5">
        {items.map((ex) => (
          <NavDestinationRow key={`${ex.key}-${ex.destination}`} exit={ex} busyKey={busyKey} onTravel={onTravel} />
        ))}
      </div>
    );

  return (
    <div>
      <div className="mb-0.5 flex min-w-0 items-center gap-1">
        <span className="min-w-0 flex-1 truncate text-ui-caption font-semibold uppercase tracking-wide text-ui-muted">
          {title}
        </span>
        <PanelExpandButton
          open={open}
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          className="shrink-0"
        />
      </div>
      {open ? (
        <div className="min-w-0" style={navSectionNestedOutdentStyles}>
          {listBody}
        </div>
      ) : null}
    </div>
  );
}

function NavPanel({
  roomExits,
  onTravelComplete,
  onPuppetLocationChanged,
}: {
  roomExits: ExitButton[];
  onTravelComplete: () => void;
  onPuppetLocationChanged: () => void;
}) {
  const router = useRouter();
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [travelError, setTravelError] = useState<string | null>(null);
  const travelLock = useRef(false);

  const filteredDestinations = useMemo(
    () => roomExits.filter((e): e is ExitButton & { destination: string } => Boolean(e.destination)),
    [roomExits],
  );

  const destinationGroups = useMemo(() => groupExits(filteredDestinations), [filteredDestinations]);

  const groupTitles = useMemo(() => destinationGroups.map((g) => g.title), [destinationGroups]);

  const groupByTitle = useMemo(
    () => new Map(destinationGroups.map((g) => [g.title, g] as const)),
    [destinationGroups],
  );

  const { order, setOrder, hydrated } = useNavRailDestinationGroupOrder(groupTitles);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const { bySection, setRowOrder, hydrated: rowOrderHydrated } = useNavRailExitRowOrder();

  const flatRowOrder = useMemo(
    () => orderedExitKeys(NAV_RAIL_EXIT_ROW_FLAT_SLUG, filteredDestinations, bySection, rowOrderHydrated),
    [filteredDestinations, bySection, rowOrderHydrated],
  );

  const flatExitByKey = useMemo(() => {
    const m = new Map<string, ExitButton & { destination: string }>();
    for (const ex of filteredDestinations) m.set(ex.key, ex);
    return m;
  }, [filteredDestinations]);

  const makeOnRowDragEnd = useCallback(
    (sectionSlug: string, rowOrder: string[]) => (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;
      const oldIndex = rowOrder.indexOf(String(active.id));
      const newIndex = rowOrder.indexOf(String(over.id));
      if (oldIndex < 0 || newIndex < 0) return;
      setRowOrder(sectionSlug, arrayMove(rowOrder, oldIndex, newIndex));
    },
    [setRowOrder],
  );

  const onDestinationGroupsDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;
      const oldIndex = order.indexOf(String(active.id));
      const newIndex = order.indexOf(String(over.id));
      if (oldIndex < 0 || newIndex < 0) return;
      setOrder(arrayMove(order, oldIndex, newIndex));
    },
    [order, setOrder],
  );

  const handleExitTravel = useCallback(
    async (destination: string) => {
      if (travelLock.current) return;
      travelLock.current = true;
      const k = `exit:${destination}`;
      setBusyKey(k);
      setTravelError(null);
      try {
        const res = await playTravel({ destination });
        const path = webNavigatePathFromPlayResult(res);
        router.push(path);
        router.refresh();
        onTravelComplete();
        queueMicrotask(() => {
          onPuppetLocationChanged();
        });
      } catch (e) {
        setTravelError(e instanceof Error ? e.message : "Travel failed.");
      } finally {
        travelLock.current = false;
        setBusyKey(null);
      }
    },
    [onPuppetLocationChanged, onTravelComplete, router],
  );

  if (filteredDestinations.length === 0) return null;

  return (
    <Panel
      panelKey="hub-exits"
      title="Destinations"
      bodyClassName="border border-cyan-900/40 bg-zinc-950/80 py-1.5 pr-1.5 pl-0 text-xs"
    >
      {travelError ? (
        <p className="mb-1 px-1.5 text-xs text-red-400" role="alert">
          {travelError}
        </p>
      ) : null}
      {destinationGroups.length <= 1 &&
      (destinationGroups[0]?.title === "Destinations" || !destinationGroups[0]) ? (
        rowOrderHydrated && filteredDestinations.length > 1 ? (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={makeOnRowDragEnd(NAV_RAIL_EXIT_ROW_FLAT_SLUG, flatRowOrder)}
          >
            <SortableContext items={flatRowOrder} strategy={verticalListSortingStrategy}>
              {flatRowOrder.map((k) => {
                const ex = flatExitByKey.get(k);
                if (!ex) return null;
                return (
                  <SortableNavDestinationRow key={k} id={k}>
                    <NavDestinationRow exit={ex} busyKey={busyKey} onTravel={handleExitTravel} />
                  </SortableNavDestinationRow>
                );
              })}
            </SortableContext>
          </DndContext>
        ) : (
          <div className="space-y-0.5">
            {filteredDestinations.map((ex) => (
              <NavDestinationRow
                key={`${ex.key}-${ex.destination}`}
                exit={ex}
                busyKey={busyKey}
                onTravel={handleExitTravel}
              />
            ))}
          </div>
        )
      ) : hydrated ? (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDestinationGroupsDragEnd}>
          <SortableContext items={order} strategy={verticalListSortingStrategy}>
            {order.map((title) => {
              const g = groupByTitle.get(title);
              if (!g) return null;
              const itemsTyped = g.items as (ExitButton & { destination: string })[];
              const slug = slugifyNavSectionTitle(title);
              const rowOrder = orderedExitKeys(slug, itemsTyped, bySection, rowOrderHydrated);
              return (
                <SortableNavDestinationGroup key={title} id={title}>
                  <NavDestinationGroup
                    title={title}
                    items={itemsTyped}
                    busyKey={busyKey}
                    onTravel={handleExitTravel}
                    rowOrder={rowOrder}
                    rowOrderHydrated={rowOrderHydrated}
                    onRowDragEnd={makeOnRowDragEnd(slug, rowOrder)}
                    sensors={sensors}
                  />
                </SortableNavDestinationGroup>
              );
            })}
          </SortableContext>
        </DndContext>
      ) : (
        <div className="space-y-1.5">
          {destinationGroups.map(({ title, items }) => {
            const itemsTyped = items as (ExitButton & { destination: string })[];
            const slug = slugifyNavSectionTitle(title);
            const rowOrder = orderedExitKeys(slug, itemsTyped, bySection, rowOrderHydrated);
            return (
              <NavDestinationGroup
                key={title}
                title={title}
                items={itemsTyped}
                busyKey={busyKey}
                onTravel={handleExitTravel}
                rowOrder={rowOrder}
                rowOrderHydrated={rowOrderHydrated}
                onRowDragEnd={makeOnRowDragEnd(slug, rowOrder)}
                sensors={sensors}
              />
            );
          })}
        </div>
      )}
    </Panel>
  );
}

const RAIL_MINI_LINK =
  "text-[10px] font-bold uppercase tracking-widest text-cyber-cyan/90 hover:text-cyber-cyan";

export function PersistentNavRail() {
  const { data, loading, error, reload, bumpPuppetLocationSeq } = useControlSurface();
  const router = useRouter();
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
          {data.canWebSwitchCharacter ? (
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
          ) : null}
          <PlayerPanel
            char={data.character}
            morality={data.missions?.morality ?? { good: 0, evil: 0, lawful: 0, chaotic: 0 }}
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
    return (
      <div className="space-y-1 text-ui-muted">
        <p>Not logged in.</p>
        <Link
          href="/login"
          className="inline-block rounded border border-cyan-900/50 bg-zinc-950/80 px-2 py-1 text-xs font-bold uppercase tracking-widest text-cyber-cyan hover:border-cyan-700/60"
        >
          Sign in
        </Link>
      </div>
    );
  })();

  return (
    <aside className="relative min-w-0 border-b border-cyan-900/40 bg-zinc-950 p-1.5 md:sticky md:top-0 md:z-20 md:h-svh md:border-b-0 md:border-r md:overflow-y-auto">
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
        <Link href="/mail" className="text-xs font-bold uppercase tracking-widest text-cyber-cyan hover:text-cyber-cyan">
          Mail
        </Link>
        <Link href="/roll" className="text-xs font-bold uppercase tracking-widest text-cyber-cyan hover:text-cyber-cyan">
          Roll
        </Link>
        <Link href="/reports" className="text-xs font-bold uppercase tracking-widest text-cyber-cyan hover:text-cyber-cyan">
          Reports
        </Link>
        {data?.canManageStaffReportsWeb ? (
          <Link
            href="/staff/reports"
            className="text-xs font-bold uppercase tracking-widest text-cyber-cyan/80 hover:text-cyber-cyan"
          >
            Staff reports
          </Link>
        ) : null}
        {data?.canStaffEngineHealthWeb ? (
          <Link href="/staff/ops-health" className={RAIL_MINI_LINK}>
            Ops health
          </Link>
        ) : null}
        {(loading || pickBusy || switchBusy) && <span className="ml-auto text-ui-caption text-ui-muted">…</span>}
      </div>

      {!data && error ? <div className="mb-1 text-red-400">{error}</div> : null}

      {railBody}

      {data?.character && data.nav && isPlacesNavContentVisible(data) ? (
        <PlacesNavPanel nav={data.nav} onReload={reload} />
      ) : null}

      <NavPanel
        roomExits={data?.roomExits ?? []}
        onTravelComplete={reload}
        onPuppetLocationChanged={bumpPuppetLocationSeq}
      />
    </aside>
  );
}
