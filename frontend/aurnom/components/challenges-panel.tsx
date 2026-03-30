"use client";

import { PanelExpandButton } from "@/components/panel-expand-button";
import type { ChallengeActive, ChallengesState } from "@/lib/ui-api";
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
      return "text-cyan-400";
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
            className={`min-w-0 truncate font-mono ${done ? "text-cyan-200" : "text-zinc-100"}`}
          >
            {entry.title}
          </div>
          <SummaryLine text={entry.summary} />
        </div>
        <div className="shrink-0 text-right">
          <div
            className={`text-[10px] font-semibold uppercase tracking-wide ${statusToneClass(entry.status)}`}
          >
            {statusLabel(entry.status)}
          </div>
          <div className="text-[10px] text-zinc-500">{formatWindowKey(entry.windowKey, entry.cadence)}</div>
          {canClaim ? (
            <button
              type="button"
              disabled={claimBusy}
              onClick={() => void onClaim(entry.challengeId, entry.windowKey)}
              className="mt-0.5 rounded border border-cyan-600/50 bg-cyan-950/60 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-cyan-300 hover:bg-cyan-900/40 disabled:opacity-40"
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
  claimBusy,
}: {
  group: CadenceGroup;
  onClaim?: (challengeId: string, windowKey: string) => void | Promise<void>;
  claimBusy?: boolean;
}) {
  const label = CADENCE_LABELS[group.cadence] ?? group.cadence;
  const completedCount = group.entries.filter(
    (e) => e.status === "complete" || e.status === "claimed",
  ).length;
  const total = group.entries.length;
  const [open, setOpen] = useDashboardPanelOpen(`challenges-cadence:${group.cadence}`, true);

  return (
    <div className="border-t border-cyan-900/25 pt-1.5 first:border-0 first:pt-0">
      <div className="flex min-w-0 items-center gap-1">
        <span className="min-w-0 flex-1 truncate text-[10px] font-bold uppercase tracking-widest text-cyan-300">
          {label}
          {completedCount > 0 ? (
            <span className="ml-1 font-mono font-normal normal-case tracking-normal">
              <span className="text-cyan-400">{completedCount}</span>
              <span className="text-zinc-500">/</span>
              <span className="text-amber-400">{total}</span>
            </span>
          ) : null}
        </span>
        <PanelExpandButton
          open={open}
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${label}`}
          className="shrink-0"
        />
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
// Main panel
// ---------------------------------------------------------------------------

type Props = {
  challenges: ChallengesState;
  onClaimChallenge?: (challengeId: string, windowKey: string) => void | Promise<void>;
  claimBusy?: boolean;
};

const PANEL_HEADER =
  "flex min-w-0 items-center gap-1 bg-cyan-900/30 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-widest";
const PANEL_BODY = "border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-[11px]";

export function ChallengesPanel({ challenges, onClaimChallenge, claimBusy }: Props) {
  const active = challenges.active ?? [];
  const history = challenges.history ?? [];
  const [panelOpen, setPanelOpen] = useDashboardPanelOpen("challenges", true);

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

  if (active.length === 0 && history.length === 0) {
    return (
      <section className="mb-1">
        <div className={PANEL_HEADER}>
          <span className="min-w-0 truncate text-cyan-300">Challenges</span>
        </div>
        <div className={PANEL_BODY}>
          <p className="text-ui-muted">No challenges tracked yet. Explore, trade, or operate a property to begin.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="mb-1">
        <div className={PANEL_HEADER}>
          <span className="min-w-0 truncate text-cyan-300">Challenges</span>
          {typeof challenges.pointsLifetime === "number" ? (
            <span className="shrink-0 font-mono text-[9px] font-normal normal-case tracking-normal text-amber-400/90">
              {challenges.pointsLifetime.toLocaleString()} pts
            </span>
          ) : null}
          <div className="ml-auto flex shrink-0 items-center gap-1 normal-case tracking-normal">
          {totalComplete > 0 || totalActive > 0 ? (
            <span className="font-mono text-[9px] font-normal">
              {totalComplete > 0 ? (
                <>
                  <span className="text-cyan-400">{totalComplete}</span>
                  <span className="text-zinc-500"> ready</span>
                </>
              ) : null}
              {totalComplete > 0 && totalActive > 0 ? <span className="text-zinc-600"> · </span> : null}
              {totalActive > 0 ? (
                <>
                  <span className="text-amber-400">{totalActive}</span>
                  <span className="text-zinc-500"> active</span>
                </>
              ) : null}
            </span>
          ) : null}
          <PanelExpandButton
            open={panelOpen}
            onClick={() => setPanelOpen((v) => !v)}
            aria-label={`${panelOpen ? "Collapse" : "Expand"} Challenges`}
          />
        </div>
      </div>
      {panelOpen ? (
        <div className={PANEL_BODY}>
          <div className="flex flex-col gap-0">
            {grouped.map((group) => (
              <CadenceSection
                key={group.cadence}
                group={group}
                onClaim={onClaimChallenge}
                claimBusy={claimBusy}
              />
            ))}
          </div>

          {history.length > 0 ? (
            <div className="mt-2 border-t border-cyan-900/25 pt-1.5">
              <div className="mb-1 text-[10px] font-bold uppercase tracking-widest text-cyan-300">Recent completions</div>
              <div className="flex flex-col gap-0.5">
                {history.slice(0, 5).map((row) => (
                  <div
                    key={`${row.challengeId}-${row.windowKey}`}
                    className="flex min-w-0 items-baseline justify-between gap-2 border-b border-zinc-800/60 pb-0.5 last:border-0 last:pb-0"
                  >
                    <span className="min-w-0 truncate font-mono text-cyan-400/90">
                      {row.challengeId.replace(/^(daily|weekly|monthly|quarter|half_year|year)\./, "")}
                    </span>
                    <span className="shrink-0 font-mono text-[10px] text-ui-muted">
                      {row.cadence} · {row.windowKey}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
