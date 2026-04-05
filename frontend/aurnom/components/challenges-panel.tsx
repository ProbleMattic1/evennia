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
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useMemo } from "react";

import { PanelExpandButton } from "@/components/panel-expand-button";
import {
  DASHBOARD_PANEL_BODY,
  DASHBOARD_PANEL_HEADER,
  DASHBOARD_PANEL_SECTION,
  DASHBOARD_PANEL_TITLE,
} from "@/lib/dashboard-panel-chrome";
import type {
  ChallengeActive,
  ChallengeHistoryRow,
  ChallengesState,
  PerkCatalogEntry,
  PointOfferWeb,
} from "@/lib/ui-api";
import { useDashboardPanelOpen } from "@/lib/use-dashboard-panel-open";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const CADENCE_LABELS: Record<string, string> = {
  daily: "Daily",
  weekly: "Weekly",
  monthly: "Monthly",
  quarter: "Quarterly",
  half_year: "Six-month",
  year: "Yearly",
};

const CADENCE_ORDER: Record<string, number> = {
  daily: 0,
  weekly: 1,
  monthly: 2,
  quarter: 3,
  half_year: 4,
  year: 5,
};

function statusLabel(status: string) {
  switch (status) {
    case "complete":
      return "Complete";
    case "claimed":
      return "Claimed";
    case "in_progress":
      return "In progress";
    case "expired":
      return "Expired";
    default:
      return status;
  }
}

/** Status line color — cyan = done/on-theme, amber = active (matches dashboard warnings). */
function statusToneClass(status: string) {
  switch (status) {
    case "complete":
    case "claimed":
      return "text-cyber-cyan";
    case "in_progress":
      return "text-amber-400";
    case "expired":
      return "text-red-400/85";
    default:
      return "text-ui-muted";
  }
}

function formatWindowKey(key: string, cadence: string) {
  if (!key) return "";
  if (cadence === "daily") {
    try {
      return new Date(key + "T00:00:00Z").toLocaleDateString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
      });
    } catch {
      return key;
    }
  }
  return key;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SummaryLine({ text }: { text: string }) {
  const parts = text.split(/(\[DEV\])/g);
  return (
    <div className="mt-0.5 font-mono text-ui-muted leading-snug">
      {parts.map((part, i) =>
        part === "[DEV]" ? (
          <span key={i} className="text-fuchsia-400/90">
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </div>
  );
}

function ChallengeRow({
  entry,
  onClaim,
  claimBusy,
}: {
  entry: ChallengeActive;
  onClaim?: (challengeId: string, windowKey: string) => void | Promise<void>;
  claimBusy?: boolean;
}) {
  const done = entry.status === "complete" || entry.status === "claimed";
  const canClaim = entry.status === "complete" && onClaim;
  return (
    <div className="border-b border-zinc-800/60 pb-1 last:border-0 last:pb-0">
      <div className="flex min-w-0 items-start gap-1">
        <div className="min-w-0 flex-1">
          <div
            className={`min-w-0 truncate font-mono ${done ? "text-ui-soft" : "text-foreground"}`}
          >
            {entry.title}
          </div>
          <SummaryLine text={entry.summary} />
        </div>
        <div className="shrink-0 text-right">
          <div
            className={`text-xs font-semibold uppercase tracking-wide ${statusToneClass(entry.status)}`}
          >
            {statusLabel(entry.status)}
          </div>
          <div className="text-xs text-ui-muted">{formatWindowKey(entry.windowKey, entry.cadence)}</div>
          {canClaim ? (
            <button
              type="button"
              disabled={claimBusy}
              onClick={() => void onClaim(entry.challengeId, entry.windowKey)}
              className="mt-0.5 rounded border border-cyan-600/50 bg-cyan-950/60 px-1.5 py-0.5 text-ui-caption font-bold uppercase tracking-wide text-cyber-cyan hover:bg-cyan-900/40 disabled:opacity-40"
            >
              Claim
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

type CadenceGroup = {
  cadence: string;
  entries: ChallengeActive[];
};

function CadenceSection({
  group,
  onClaim,
  onClaimCadence,
  claimBusy,
}: {
  group: CadenceGroup;
  onClaim?: (challengeId: string, windowKey: string) => void | Promise<void>;
  onClaimCadence?: (cadence: string) => void | Promise<void>;
  claimBusy?: boolean;
}) {
  const label = CADENCE_LABELS[group.cadence] ?? group.cadence;
  const completedCount = group.entries.filter(
    (e) => e.status === "complete" || e.status === "claimed",
  ).length;
  const claimableCount = group.entries.filter((e) => e.status === "complete").length;
  const total = group.entries.length;
  const [open, setOpen] = useDashboardPanelOpen(`challenges-cadence:${group.cadence}`, true);

  return (
    <div className="border-t border-cyan-900/25 pt-1.5 first:border-0 first:pt-0">
      <div className="flex min-w-0 flex-wrap items-start gap-x-1 gap-y-1 sm:items-center">
        <span className="min-w-0 flex-1 basis-[min(100%,10rem)] truncate text-xs font-bold uppercase tracking-widest text-ui-soft sm:basis-auto">
          {label}
          {total > 0 ? (
            <span className="ml-1 font-mono font-normal normal-case tracking-normal">
              <span className="text-zinc-200">{completedCount}</span>
              <span className="text-ui-muted">/</span>
              <span className="text-amber-400">{total}</span>
            </span>
          ) : null}
        </span>
        <div className="ml-auto flex shrink-0 items-center gap-1">
          {claimableCount > 0 && onClaimCadence ? (
            <button
              type="button"
              disabled={claimBusy}
              onClick={() => void onClaimCadence(group.cadence)}
              className="shrink-0 rounded border border-amber-600/50 bg-amber-950/40 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-400 hover:bg-amber-900/30 disabled:opacity-40"
            >
              Claim all
            </button>
          ) : null}
          <PanelExpandButton
            open={open}
            onClick={() => setOpen((v) => !v)}
            aria-label={`${open ? "Collapse" : "Expand"} ${label}`}
            className="shrink-0"
          />
        </div>
      </div>
      {open ? (
        <div className="mt-1 space-y-1">
          {group.entries.map((entry) => (
            <ChallengeRow
              key={`${entry.challengeId}-${entry.windowKey}`}
              entry={entry}
              onClaim={onClaim}
              claimBusy={claimBusy}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Perk loadout (opaque; titles from server catalog only)
// ---------------------------------------------------------------------------

function SortableEquippedPerkRow({
  id,
  title,
  onUnequip,
  disabled,
}: {
  id: string;
  title: string;
  onUnequip: () => void;
  disabled?: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 20 : undefined,
  };
  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex min-w-0 items-stretch gap-1 rounded border border-cyan-800/35 bg-zinc-900/55 py-0.5 pl-0.5 pr-1"
    >
      <button
        type="button"
        className="mt-0.5 h-fit shrink-0 cursor-grab touch-none p-0.5 text-ui-muted hover:text-cyber-cyan active:cursor-grabbing disabled:opacity-30"
        aria-label="Drag to reorder perk"
        disabled={disabled}
        {...listeners}
        {...attributes}
      >
        ⋮⋮
      </button>
      <div className="min-w-0 flex-1 py-0.5 font-mono text-[11px] text-ui-soft">{title}</div>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onUnequip()}
        className="shrink-0 self-center rounded border border-zinc-600/50 px-1 py-0.5 text-[10px] uppercase tracking-wide text-ui-muted hover:border-amber-700/40 hover:text-amber-400 disabled:opacity-40"
      >
        Bench
      </button>
    </div>
  );
}

function PerkLoadoutBlock(props: {
  challenges: ChallengesState;
  onSetLoadout?: (equippedPerkIds: string[]) => void | Promise<void>;
  loadoutBusy?: boolean;
}) {
  const { challenges, onSetLoadout, loadoutBusy } = props;
  const [open, setOpen] = useDashboardPanelOpen("challenges-perk-loadout", true);
  const slots = challenges.perkSlotTotal ?? 2;
  const equipped = challenges.equippedPerks ?? [];
  const owned = challenges.ownedPerks ?? [];

  const catalogById = useMemo(() => {
    const m = new Map<string, PerkCatalogEntry>();
    for (const row of challenges.perkCatalog ?? []) {
      m.set(row.id, row);
    }
    return m;
  }, [challenges.perkCatalog]);

  const titleFor = (id: string) => catalogById.get(id)?.title ?? id;

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const benchIds = owned.filter((id) => !equipped.includes(id));
  const busy = Boolean(loadoutBusy);

  function handleDragEnd(event: DragEndEvent) {
    if (!onSetLoadout || busy) return;
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = equipped.indexOf(String(active.id));
    const newIndex = equipped.indexOf(String(over.id));
    if (oldIndex < 0 || newIndex < 0) return;
    const next = arrayMove(equipped, oldIndex, newIndex);
    void onSetLoadout(next);
  }

  function equip(id: string) {
    if (!onSetLoadout || busy) return;
    if (equipped.length >= slots) return;
    if (equipped.includes(id)) return;
    void onSetLoadout([...equipped, id]);
  }

  function unequip(id: string) {
    if (!onSetLoadout || busy) return;
    void onSetLoadout(equipped.filter((x) => x !== id));
  }

  return (
    <div className="mt-2 border-t border-cyan-900/25 pt-1.5">
      <div className="flex min-w-0 flex-wrap items-start gap-x-1 gap-y-1 sm:items-center">
        <span className="min-w-0 flex-1 truncate text-xs font-bold uppercase tracking-widest text-ui-soft">
          Passive perks
        </span>
        <span className="shrink-0 font-mono text-[10px] text-ui-caption text-ui-muted">
          {equipped.length}/{slots} equipped
        </span>
        <div className="ml-auto flex shrink-0 items-center">
          <PanelExpandButton
            open={open}
            onClick={() => setOpen((v) => !v)}
            aria-label={`${open ? "Collapse" : "Expand"} Passive perks`}
            className="shrink-0"
          />
        </div>
      </div>
      {open ? (
        <div className="mt-1 space-y-2">
          {owned.length === 0 ? (
            <p className="text-ui-muted">
              No passives owned yet. Unlock grants in the point store, then equip up to {slots} at a time.
            </p>
          ) : null}

          {equipped.length > 0 && onSetLoadout ? (
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={equipped} strategy={verticalListSortingStrategy}>
                <div className="flex flex-col gap-1">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-ui-muted">Equipped (drag to reorder)</p>
                  {equipped.map((id) => (
                    <SortableEquippedPerkRow
                      key={id}
                      id={id}
                      title={titleFor(id)}
                      disabled={busy}
                      onUnequip={() => unequip(id)}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          ) : equipped.length > 0 ? (
            <ul className="flex flex-col gap-0.5">
              {equipped.map((id) => (
                <li key={id} className="font-mono text-[11px] text-ui-soft">
                  {titleFor(id)}
                </li>
              ))}
            </ul>
          ) : null}

          {benchIds.length > 0 ? (
            <div>
              <p className="mb-0.5 text-[10px] font-bold uppercase tracking-wide text-ui-muted">Bench</p>
              <ul className="flex flex-col gap-1">
                {benchIds.map((id) => {
                  const row = catalogById.get(id);
                  const canEquip = Boolean(onSetLoadout) && equipped.length < slots && !busy;
                  return (
                    <li
                      key={id}
                      className="flex flex-col gap-0.5 border-b border-zinc-800/50 pb-1 last:border-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between sm:gap-2"
                    >
                      <div className="min-w-0">
                        <div className="font-mono text-ui-soft">{row?.title ?? id}</div>
                        {row?.summary ? <p className="text-ui-muted">{row.summary}</p> : null}
                      </div>
                      {onSetLoadout ? (
                        <button
                          type="button"
                          disabled={!canEquip}
                          onClick={() => equip(id)}
                          className="shrink-0 self-end rounded border border-cyan-700/40 bg-cyan-950/30 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-cyber-cyan hover:bg-cyan-900/25 disabled:opacity-40 sm:self-start"
                        >
                          Equip
                        </button>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Point store (challenge points only; no credits)
// ---------------------------------------------------------------------------

function PointStoreBlock(props: {
  offers: PointOfferWeb[];
  onPurchase?: (offerId: string) => void | Promise<void>;
  purchaseBusy?: boolean;
}) {
  const { offers, onPurchase, purchaseBusy } = props;
  const [open, setOpen] = useDashboardPanelOpen("challenges-point-store", true);
  if (!offers.length) return null;
  return (
    <div className="mt-2 border-t border-cyan-900/25 pt-1.5">
      <div className="flex min-w-0 flex-wrap items-start gap-x-1 gap-y-1 sm:items-center">
        <span className="min-w-0 flex-1 truncate text-xs font-bold uppercase tracking-widest text-ui-soft">
          Point store
        </span>
        <div className="ml-auto flex shrink-0 items-center">
          <PanelExpandButton
            open={open}
            onClick={() => setOpen((v) => !v)}
            aria-label={`${open ? "Collapse" : "Expand"} Point store`}
            className="shrink-0"
          />
        </div>
      </div>
      {open ? (
        <ul className="mt-1 flex flex-col gap-1">
          {offers.map((o) => (
            <li
              key={o.id}
              className="flex flex-col gap-0.5 border-b border-zinc-800/50 pb-1 last:border-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between sm:gap-2"
            >
              <div className="min-w-0">
                <div className="font-mono text-ui-soft">{o.title}</div>
                {o.summary ? <p className="text-ui-muted">{o.summary}</p> : null}
                <div className="mt-0.5 font-mono text-[10px] text-ui-caption">
                  LT {o.costLifetime}
                  {o.costSeason > 0 ? ` · SS ${o.costSeason}` : ""}
                  {o.purchasedCount > 0 ? ` · owned ×${o.purchasedCount}` : ""}
                  {!o.prerequisitesMet ? " · locked (prereq)" : null}
                  {!o.seasonOk ? " · wrong season" : null}
                  {o.soldOut ? " · maxed" : null}
                </div>
              </div>
              {onPurchase ? (
                <button
                  type="button"
                  disabled={purchaseBusy || !o.canPurchase}
                  onClick={() => void onPurchase(o.id)}
                  className="shrink-0 self-end rounded border border-cyan-700/40 bg-cyan-950/30 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-cyber-cyan hover:bg-cyan-900/25 disabled:opacity-40 sm:self-start"
                >
                  Buy
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function RecentCompletionsBlock({ history }: { history: ChallengeHistoryRow[] }) {
  const [open, setOpen] = useDashboardPanelOpen("challenges-recent-completions", true);
  if (!history.length) return null;
  return (
    <div className="mt-2 border-t border-cyan-900/25 pt-1.5">
      <div className="flex min-w-0 flex-wrap items-start gap-x-1 gap-y-1 sm:items-center">
        <span className="min-w-0 flex-1 truncate text-xs font-bold uppercase tracking-widest text-ui-soft">
          Recent completions
        </span>
        <div className="ml-auto flex shrink-0 items-center">
          <PanelExpandButton
            open={open}
            onClick={() => setOpen((v) => !v)}
            aria-label={`${open ? "Collapse" : "Expand"} Recent completions`}
            className="shrink-0"
          />
        </div>
      </div>
      {open ? (
        <div className="mt-1 flex flex-col gap-0.5">
          {history.slice(0, 5).map((row) => (
            <div
              key={`${row.challengeId}-${row.windowKey}`}
              className="flex min-w-0 flex-col gap-0.5 border-b border-zinc-800/60 pb-1 last:border-0 last:pb-0 sm:flex-row sm:items-baseline sm:justify-between sm:gap-2 sm:pb-0.5"
            >
              <span className="min-w-0 break-words font-mono text-ui-soft sm:truncate">
                {row.title}
              </span>
              <span className="shrink-0 self-end font-mono text-xs tabular-nums text-ui-muted sm:self-auto">
                {row.cadence} · {row.windowKey}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

type Props = {
  challenges: ChallengesState;
  onClaimChallenge?: (challengeId: string, windowKey: string) => void | Promise<void>;
  onClaimCadence?: (cadence: string) => void | Promise<void>;
  /** Claim every cadence that has at least one completed (unclaimed) challenge; ordered for stable UX. */
  onClaimAll?: (cadences: string[]) => void | Promise<void>;
  claimBusy?: boolean;
  onPurchaseOffer?: (offerId: string) => void | Promise<void>;
  purchaseBusy?: boolean;
  onSetPerkLoadout?: (equippedPerkIds: string[]) => void | Promise<void>;
  perkLoadoutBusy?: boolean;
};

export function ChallengesPanel({
  challenges,
  onClaimChallenge,
  onClaimCadence,
  onClaimAll,
  claimBusy,
  onPurchaseOffer,
  purchaseBusy,
  onSetPerkLoadout,
  perkLoadoutBusy,
}: Props) {
  const active = challenges.active ?? [];
  const history = challenges.history ?? [];
  const pointOffers = challenges.pointOffers ?? [];
  const [panelOpen, setPanelOpen] = useDashboardPanelOpen("challenges", true);

  const cadencesToClaimAll = [...new Set(active.filter((e) => e.status === "complete").map((e) => e.cadence ?? "daily"))].sort(
    (a, b) => (CADENCE_ORDER[a] ?? 99) - (CADENCE_ORDER[b] ?? 99),
  );

  const grouped: CadenceGroup[] = Object.values(
    active.reduce<Record<string, CadenceGroup>>((acc, entry) => {
      const cad = entry.cadence ?? "daily";
      if (!acc[cad]) acc[cad] = { cadence: cad, entries: [] };
      acc[cad].entries.push(entry);
      return acc;
    }, {}),
  ).sort((a, b) => (CADENCE_ORDER[a.cadence] ?? 99) - (CADENCE_ORDER[b.cadence] ?? 99));

  const totalComplete = active.filter(
    (e) => e.status === "complete" || e.status === "claimed",
  ).length;
  const totalActive = active.filter((e) => e.status === "in_progress").length;

  const ownedPerksCount = challenges.ownedPerks?.length ?? 0;

  if (active.length === 0 && history.length === 0 && pointOffers.length === 0 && ownedPerksCount === 0) {
    return (
      <section className={DASHBOARD_PANEL_SECTION}>
        <div className={DASHBOARD_PANEL_HEADER}>
          <span className={DASHBOARD_PANEL_TITLE}>Challenges</span>
        </div>
        <div className={DASHBOARD_PANEL_BODY}>
          <p className="text-ui-muted">No challenges tracked yet. Explore, trade, or operate a property to begin.</p>
        </div>
      </section>
    );
  }

  return (
    <section className={DASHBOARD_PANEL_SECTION}>
      <div className={`${DASHBOARD_PANEL_HEADER} flex-nowrap`}>
        <div className="flex min-w-0 items-center gap-2">
          <span className={`${DASHBOARD_PANEL_TITLE} flex-1`}>Challenges</span>
          {typeof challenges.pointsLifetime === "number" ? (
            <span className="shrink-0 font-mono text-ui-caption font-normal normal-case tracking-normal text-amber-400/90">
              LT {challenges.pointsLifetime.toLocaleString()}
              {typeof challenges.pointsSeason === "number" && challenges.pointsSeason >= 0 ? (
                <>
                  {" "}
                  · SS {challenges.pointsSeason.toLocaleString()}
                </>
              ) : null}
            </span>
          ) : null}
        </div>
        <div className="ml-auto flex min-w-0 shrink-0 items-center justify-end gap-1 normal-case tracking-normal">
          {totalComplete > 0 || totalActive > 0 ? (
            <span className="min-w-0 truncate text-right font-mono text-ui-caption font-normal whitespace-nowrap">
              {totalComplete > 0 ? (
                <>
                  <span className="text-cyber-cyan">{totalComplete}</span>
                  <span className="text-ui-muted"> ready</span>
                </>
              ) : null}
              {totalComplete > 0 && totalActive > 0 ? <span className="text-ui-muted"> · </span> : null}
              {totalActive > 0 ? (
                <>
                  <span className="text-amber-400">{totalActive}</span>
                  <span className="text-ui-muted"> active</span>
                </>
              ) : null}
            </span>
          ) : null}
          {cadencesToClaimAll.length > 0 && onClaimAll ? (
            <button
              type="button"
              disabled={claimBusy}
              onClick={() => void onClaimAll(cadencesToClaimAll)}
              className="shrink-0 rounded border border-amber-600/50 bg-amber-950/40 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-400 hover:bg-amber-900/30 disabled:opacity-40"
            >
              Claim all
            </button>
          ) : null}
          <PanelExpandButton
            open={panelOpen}
            onClick={() => setPanelOpen((v) => !v)}
            aria-label={`${panelOpen ? "Collapse" : "Expand"} Challenges`}
          />
        </div>
      </div>
      {panelOpen ? (
        <div className={DASHBOARD_PANEL_BODY}>
          {active.length > 0 ? (
            <div className="flex flex-col gap-0">
              {grouped.map((group) => (
                <CadenceSection
                  key={group.cadence}
                  group={group}
                  onClaim={onClaimChallenge}
                  onClaimCadence={onClaimCadence}
                  claimBusy={claimBusy}
                />
              ))}
            </div>
          ) : (
            <p className="mb-2 text-ui-muted">
              No active cadence challenges right now. Complete tasks to earn lifetime and seasonal points.
            </p>
          )}

          <PointStoreBlock
            offers={pointOffers}
            onPurchase={onPurchaseOffer}
            purchaseBusy={purchaseBusy}
          />

          <PerkLoadoutBlock
            challenges={challenges}
            onSetLoadout={onSetPerkLoadout}
            loadoutBusy={perkLoadoutBusy}
          />

          <RecentCompletionsBlock history={history} />
        </div>
      ) : null}
    </section>
  );
}
