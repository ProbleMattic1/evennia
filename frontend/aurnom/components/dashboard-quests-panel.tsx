"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { groupExits } from "@/components/exit-grid";
import { PanelExpandButton } from "@/components/panel-expand-button";
import { PipelineMatrixOverlay } from "@/components/pipeline-matrix-overlay";
import type {
  ExitButton,
  QuestActive,
  QuestChoice,
  QuestObjective,
  QuestOpportunity,
  QuestResolvePath,
  QuestsState,
} from "@/lib/ui-api";
import { acceptQuest, chooseQuest, playInteract, playTravel, webNavigatePathFromPlayResult } from "@/lib/ui-api";

export type DashboardQuestsEmbeddedProps = {
  quests: QuestsState;
  /** ``_room_exits(char.location)`` from control surface; same facts as the room dialog / play/travel. */
  roomExits?: ExitButton[];
  onChanged: () => void;
  /** When false, parent renders a single shared Destinations block. */
  includeDestinations?: boolean;
};

type ChoiceDialogState = {
  quest: QuestActive;
  choice: QuestChoice;
};

function interactionKeysFromResolvePaths(paths: QuestResolvePath[] | undefined): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const p of paths ?? []) {
    if (p.via !== "interaction") continue;
    for (const k of p.interactionKeysAny ?? []) {
      const key = k.trim().toLowerCase();
      if (!key || seen.has(key)) continue;
      seen.add(key);
      out.push(k);
    }
  }
  return out;
}

function signalHintsFromResolvePaths(paths: QuestResolvePath[] | undefined): string[] {
  const hints: string[] = [];
  for (const p of paths ?? []) {
    if (p.via !== "signal") continue;
    const sig = p.signal ?? "event";
    const enc = p.match && typeof p.match.encounter_id === "string" ? p.match.encounter_id : null;
    hints.push(enc ? `${sig} · encounter_id: ${enc}` : `${sig}`);
  }
  return hints;
}

/**
 * Main-quest lists and dialogs for embedding inside the combined Missions and Quests dashboard panel.
 * Omits game log and (by default) duplicates no room exit list — parent supplies shared Destinations.
 */
export function DashboardQuestsEmbedded({
  quests,
  roomExits = [],
  onChanged,
  includeDestinations = false,
}: DashboardQuestsEmbeddedProps) {
  const router = useRouter();

  const opportunities = quests.opportunities ?? [];
  const active = quests.active ?? [];
  const completed = quests.completed ?? [];

  const decisionsPending = useMemo(
    () => active.filter((q) => q.currentObjective?.kind === "choice").length,
    [active],
  );

  const filteredRoomDestinations = useMemo(
    () =>
      roomExits.filter((e): e is ExitButton & { destination: string } => Boolean(e.destination)),
    [roomExits],
  );

  const destinationGroups = useMemo(() => groupExits(filteredRoomDestinations), [filteredRoomDestinations]);

  const availableStorageKey = "aurnom:dashboard-panel:quests:available";
  const completedStorageKey = "aurnom:dashboard-panel:quests:completed";
  const exitsStorageKey = "aurnom:dashboard-panel:quests:exits";
  const [availableOpen, setAvailableOpen] = useState(() => {
    if (typeof window === "undefined") return true;
    try {
      const raw = window.sessionStorage.getItem(availableStorageKey);
      return raw == null ? true : raw === "1";
    } catch {
      return true;
    }
  });
  const [completedOpen, setCompletedOpen] = useState(() => {
    if (typeof window === "undefined") return true;
    try {
      const raw = window.sessionStorage.getItem(completedStorageKey);
      return raw == null ? true : raw === "1";
    } catch {
      return true;
    }
  });
  const [exitsOpen, setExitsOpen] = useState(() => {
    if (typeof window === "undefined") return true;
    try {
      const raw = window.sessionStorage.getItem(exitsStorageKey);
      return raw == null ? true : raw === "1";
    } catch {
      return true;
    }
  });

  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  const [acceptOpp, setAcceptOpp] = useState<QuestOpportunity | null>(null);
  const [choiceDialog, setChoiceDialog] = useState<ChoiceDialogState | null>(null);
  const [detailQuest, setDetailQuest] = useState<QuestActive | null>(null);

  function toggleAvailableOpen() {
    setAvailableOpen((v) => {
      const next = !v;
      try {
        window.sessionStorage.setItem(availableStorageKey, next ? "1" : "0");
      } catch {
        // ignore
      }
      return next;
    });
  }

  function toggleCompletedOpen() {
    setCompletedOpen((v) => {
      const next = !v;
      try {
        window.sessionStorage.setItem(completedStorageKey, next ? "1" : "0");
      } catch {
        // ignore
      }
      return next;
    });
  }

  function toggleExitsOpen() {
    setExitsOpen((v) => {
      const next = !v;
      try {
        window.sessionStorage.setItem(exitsStorageKey, next ? "1" : "0");
      } catch {
        // ignore
      }
      return next;
    });
  }

  async function run<R extends { message?: string }>(
    key: string,
    fn: () => Promise<R>
  ): Promise<R | undefined> {
    if (busyKey) return undefined;
    setBusyKey(key);
    setFlash(null);
    try {
      const res = await fn();
      setFlash(res.message ?? "OK");
      onChanged();
      return res;
    } catch (e) {
      setFlash(e instanceof Error ? e.message : "Action failed");
      return undefined;
    } finally {
      setBusyKey(null);
    }
  }

  function labelForInteractionKey(key: string): string {
    if (key.startsWith("askguide")) {
      const topic = key.split(":")[1];
      return `Ask guide (${topic ?? "default"})`;
    }
    if (key === "survey") return "Run survey";
    if (key === "contractboard") return "Procurement board";
    if (key.startsWith("contractboard:")) {
      const part = key.split(":")[1];
      return part ? `Procurement board (${part})` : "Procurement board";
    }
    if (key === "frontier:kiosk") {
      return "Transit kiosk";
    }
    if (key.startsWith("parcel:")) {
      return `Parcel: ${key.split(":")[1] ?? "npc"}`;
    }
    if (key === "dock_crew_rumor") return "Listen to dock crew";
    if (key === "dock_shakedown_pay") return "Pay the shakedown";
    if (key === "dock_sneak_service_tunnel") return "Use service tunnel";
    return key;
  }

  async function handleAccept(op: QuestOpportunity) {
    await run(`q:accept:${op.id}`, async () => acceptQuest({ opportunityId: op.id }));
    setAcceptOpp(null);
  }

  async function handleChoose(q: QuestActive, c: QuestChoice) {
    await run(`q:choose:${q.id}:${c.id}`, async () => chooseQuest({ questId: q.id, choiceId: c.id }));
    setChoiceDialog(null);
  }

  async function handleTravel(q: QuestActive, roomKey: string) {
    const res = await run(`q:travel:${q.id}:${roomKey}`, async () => playTravel({ destination: roomKey }));
    if (res) {
      router.push(webNavigatePathFromPlayResult(res));
      router.refresh();
    }
  }

  async function handleExitTravel(destination: string) {
    const res = await run(`q:exit:${destination}`, async () => playTravel({ destination }));
    if (res) {
      router.push(webNavigatePathFromPlayResult(res));
      router.refresh();
    }
  }

  async function handleInteract(q: QuestActive, interactionKey: string) {
    await run(`q:interact:${q.id}:${interactionKey}`, async () => playInteract({ interactionKey }));
    router.refresh();
  }

  function renderObjectiveActions(q: QuestActive, obj: QuestObjective) {
    const isChoice = obj.kind === "choice" && (obj.choices?.length ?? 0) > 0;

    return (
      <>
        {obj.kind === "visit_room" && (obj.roomKeysAny?.length ?? 0) > 0 ? (
          <div className="mt-0.5 flex flex-wrap gap-1">
            {obj.roomKeysAny!.map((roomKey) => {
              const k = `q:travel:${q.id}:${roomKey}`;
              return (
                <TinyButton key={k} onClick={() => handleTravel(q, roomKey)} disabled={busyKey === k}>
                  {busyKey === k ? "Traveling…" : `Go: ${roomKey}`}
                </TinyButton>
              );
            })}
          </div>
        ) : null}

        {obj.kind === "interaction" && (obj.interactionKeysAny?.length ?? 0) > 0 ? (
          <div className="mt-0.5 flex flex-wrap gap-1">
            {obj.interactionKeysAny!.map((interactionKey) => {
              const k = `q:interact:${q.id}:${interactionKey}`;
              return (
                <TinyButton
                  key={k}
                  onClick={() => handleInteract(q, interactionKey)}
                  disabled={busyKey === k}
                >
                  {busyKey === k ? "Running…" : labelForInteractionKey(interactionKey)}
                </TinyButton>
              );
            })}
          </div>
        ) : null}

        {obj.kind === "resolve_situation" ? (
          <div className="mt-0.5 space-y-0.5">
            <div className="text-ui-caption text-ui-muted">
              Win the matching combat encounter (server) or complete an interaction below.
            </div>
            {signalHintsFromResolvePaths(obj.paths).map((hint) => (
              <div key={hint} className="text-ui-caption text-ui-soft">
                Combat path: {hint}
              </div>
            ))}
            {interactionKeysFromResolvePaths(obj.paths).length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {interactionKeysFromResolvePaths(obj.paths).map((interactionKey) => {
                  const k = `q:interact:${q.id}:${interactionKey}`;
                  return (
                    <TinyButton
                      key={k}
                      onClick={() => handleInteract(q, interactionKey)}
                      disabled={busyKey === k}
                    >
                      {busyKey === k ? "Running…" : labelForInteractionKey(interactionKey)}
                    </TinyButton>
                  );
                })}
              </div>
            ) : null}
          </div>
        ) : null}

        {isChoice ? (
          <div className="mt-0.5 flex flex-wrap gap-1">
            {obj.choices!.map((c) => (
              <TinyButton key={`${q.id}:${c.id}`} onClick={() => setChoiceDialog({ quest: q, choice: c })}>
                {c.label}
              </TinyButton>
            ))}
          </div>
        ) : null}
      </>
    );
  }

  return (
    <>
      <div className="mt-1.5">
        <div className="flex min-w-0 items-center gap-1 rounded-t border border-b-0 border-violet-900/40 bg-violet-900/25 px-1.5 py-0.5 text-xs font-bold uppercase tracking-widest">
          <span className="min-w-0 truncate text-violet-300">Main quests</span>
          <div className="ml-auto flex min-w-0 shrink-0 items-center gap-1 normal-case tracking-normal">
            <span className="font-mono text-ui-caption font-normal">
              <span className="text-ui-muted">(</span>
              <span className="text-violet-300">{active.length}</span>
              <span className="text-ui-muted"> active / </span>
              <span className="text-amber-400">{opportunities.length}</span>
              <span className="text-ui-muted"> avail)</span>
              <span className="text-ui-muted"> · </span>
              <span className="text-ui-muted">decisions pending: </span>
              <span className={decisionsPending > 0 ? "text-amber-400" : "text-violet-300"}>{decisionsPending}</span>
            </span>
          </div>
        </div>

        <div className="rounded-b border border-violet-900/40 bg-zinc-950/80 p-1.5 text-xs">
          {flash ? (
            <div className="mb-1 rounded border border-violet-900/40 bg-zinc-950 px-1.5 py-1 text-xs text-foreground">
              <span className="text-violet-300">»</span> {flash}
              <button type="button" className="ml-2 text-ui-muted hover:text-foreground" onClick={() => setFlash(null)}>
                ×
              </button>
            </div>
          ) : null}

          <div className="space-y-1">
            {active.length > 0 ? (
              <div>
                <div className="text-xs uppercase text-violet-300/90">Active</div>
                <div className="mt-0.5 space-y-1">
                  {active.map((q) => {
                    const obj = q.currentObjective ?? null;
                    const prompt = obj?.text ?? obj?.prompt ?? null;

                    return (
                      <div key={q.id} className="border-b border-zinc-800/60 pb-1 last:border-0 last:pb-0">
                        <div className="flex min-w-0 items-baseline gap-2">
                          <button
                            type="button"
                            className="min-w-0 truncate text-left font-semibold text-foreground hover:text-violet-300"
                            onClick={() => setDetailQuest(q)}
                          >
                            {q.title}
                          </button>
                          <span className="ml-auto shrink-0 text-ui-caption text-ui-muted">{q.status}</span>
                        </div>

                        {prompt ? <div className="mt-0.5 text-ui-muted">{prompt}</div> : null}

                        {obj ? renderObjectiveActions(q, obj) : null}
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : null}

            {opportunities.length > 0 ? (
              <div>
                <div className="flex items-center text-xs uppercase text-violet-300/90">
                  <span>Available</span>
                  <PanelExpandButton
                    open={availableOpen}
                    onClick={toggleAvailableOpen}
                    aria-label={`${availableOpen ? "Collapse" : "Expand"} Available quests`}
                    className="ml-auto shrink-0"
                  />
                </div>
                {availableOpen ? (
                  <div className="mt-0.5 max-h-[min(280px,45vh)] min-h-[48px] space-y-0.5 overflow-y-auto overflow-x-hidden border border-violet-900/40 bg-zinc-950/80 p-1.5 pr-2 [scrollbar-gutter:stable]">
                    {opportunities.map((op) => (
                      <div key={op.id} className="flex min-w-0 items-baseline gap-2">
                        <button
                          type="button"
                          className="min-w-0 flex-1 truncate text-left text-ui-muted hover:text-violet-300"
                          onClick={() => setAcceptOpp(op)}
                          title={op.summary}
                        >
                          {op.title}
                        </button>
                        <TinyButton variant="pink" onClick={() => setAcceptOpp(op)}>
                          Accept…
                        </TinyButton>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}

            {completed.length > 0 ? (
              <div>
                <div className="flex items-center text-xs uppercase text-violet-300/90">
                  <span>{`Completed (${completed.length})`}</span>
                  <PanelExpandButton
                    open={completedOpen}
                    onClick={toggleCompletedOpen}
                    aria-label={`${completedOpen ? "Collapse" : "Expand"} Completed quests`}
                    className="ml-auto shrink-0"
                  />
                </div>
                {completedOpen ? (
                  <div className="mt-0.5 max-h-[min(8.75rem,30vh)] min-h-[36px] space-y-0.5 overflow-y-auto overflow-x-hidden border border-violet-900/40 bg-zinc-950/80 p-1.5 pr-2 [scrollbar-gutter:stable]">
                    {completed.map((q) => (
                      <div key={q.id} className="flex min-w-0 items-baseline gap-2">
                        <span className="min-w-0 flex-1 truncate text-ui-muted">{q.title}</span>
                        {q.completedAt ? (
                          <span className="shrink-0 text-ui-caption text-ui-soft">
                            {new Date(q.completedAt).toLocaleString()}
                          </span>
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}

            {active.length === 0 && opportunities.length === 0 ? (
              <div className="text-ui-muted">No main quests available.</div>
            ) : null}
          </div>

          {includeDestinations && roomExits.some((e) => e.destination) ? (
            <div className="mt-1.5 rounded border border-cyan-900/40 bg-zinc-950/80 p-1.5">
              <div className="mb-0.5 flex items-center text-xs uppercase tracking-wide text-cyber-cyan">
                <span>Destinations</span>
                <PanelExpandButton
                  open={exitsOpen}
                  onClick={toggleExitsOpen}
                  aria-label={`${exitsOpen ? "Collapse" : "Expand"} Destinations`}
                  className="ml-auto shrink-0"
                />
              </div>
              {exitsOpen ? (
                destinationGroups.length <= 1 &&
                (destinationGroups[0]?.title === "Destinations" || !destinationGroups[0]) ? (
                  <div className="mt-0.5 flex flex-wrap gap-1">
                    {filteredRoomDestinations.map((ex) => {
                      const k = `q:exit:${ex.destination}`;
                      return (
                        <TinyButton
                          key={`${ex.key}-${ex.destination}`}
                          variant="cyan"
                          onClick={() => handleExitTravel(ex.destination)}
                          disabled={busyKey === k}
                        >
                          {busyKey === k ? "Moving…" : ex.label}
                        </TinyButton>
                      );
                    })}
                  </div>
                ) : (
                  <div className="mt-0.5 flex flex-col gap-2">
                    {destinationGroups.map(({ title, items }) => (
                      <div key={title}>
                        <div className="mb-0.5 text-xs uppercase tracking-wide text-cyber-cyan">{title}</div>
                        <div className="flex flex-wrap gap-1">
                          {items.map((ex) => {
                            const k = `q:exit:${ex.destination}`;
                            return (
                              <TinyButton
                                key={`${ex.key}-${ex.destination}`}
                                variant="cyan"
                                onClick={() => handleExitTravel(ex.destination!)}
                                disabled={busyKey === k}
                              >
                                {busyKey === k ? "Moving…" : ex.label}
                              </TinyButton>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      {acceptOpp ? (
        <OverlayDialog title="Accept quest" onClose={() => setAcceptOpp(null)}>
          <div className="space-y-1">
            <div className="text-xs font-semibold text-foreground">{acceptOpp.title}</div>
            <div className="text-ui-muted">{acceptOpp.summary}</div>

            <div className="mt-2 flex items-center gap-1">
              <TinyButton
                onClick={() => handleAccept(acceptOpp)}
                disabled={busyKey === `q:accept:${acceptOpp.id}`}
              >
                {busyKey === `q:accept:${acceptOpp.id}` ? "Accepting…" : "Confirm accept"}
              </TinyButton>
              <TinyButton onClick={() => setAcceptOpp(null)}>Cancel</TinyButton>
            </div>
          </div>
        </OverlayDialog>
      ) : null}

      {choiceDialog ? (
        <OverlayDialog title="Decide" onClose={() => setChoiceDialog(null)}>
          <div className="space-y-1">
            <div className="text-xs font-semibold text-foreground">{choiceDialog.quest.title}</div>
            <div className="text-ui-muted">
              {choiceDialog.quest.currentObjective?.prompt ?? choiceDialog.quest.currentObjective?.text}
            </div>

            <div className="mt-2 rounded border border-violet-900/40 bg-zinc-950 p-1.5">
              <div className="text-xs uppercase tracking-wide text-ui-muted">Choice</div>
              <div className="text-foreground">{choiceDialog.choice.label}</div>

              {choiceDialog.choice.outcome ? (
                <div className="mt-1 text-ui-muted">
                  <span className="text-ui-muted">Outcome:</span> {choiceDialog.choice.outcome}
                </div>
              ) : null}
            </div>

            <div className="mt-2 flex items-center gap-1">
              <TinyButton
                onClick={() => handleChoose(choiceDialog.quest, choiceDialog.choice)}
                disabled={busyKey === `q:choose:${choiceDialog.quest.id}:${choiceDialog.choice.id}`}
              >
                {busyKey === `q:choose:${choiceDialog.quest.id}:${choiceDialog.choice.id}`
                  ? "Submitting…"
                  : "Confirm"}
              </TinyButton>
              <TinyButton onClick={() => setChoiceDialog(null)}>Cancel</TinyButton>
            </div>
          </div>
        </OverlayDialog>
      ) : null}

      {detailQuest ? (
        <OverlayDialog title="Quest detail" onClose={() => setDetailQuest(null)}>
          <div className="space-y-1">
            <div className="text-xs font-semibold text-foreground">{detailQuest.title}</div>
            {detailQuest.summary ? <div className="text-ui-muted">{detailQuest.summary}</div> : null}

            {detailQuest.choices && detailQuest.choices.length > 0 ? (
              <div className="mt-2">
                <div className="text-xs uppercase text-ui-muted">Choice history</div>
                <div className="mt-0.5 space-y-0.5">
                  {detailQuest.choices.slice(-6).map((c, idx) => (
                    <div key={`${c.objectiveId}:${c.choiceId}:${idx}`} className="text-xs text-ui-muted">
                      <span className="text-ui-muted">{new Date(c.chosenAt).toLocaleString()}:</span>{" "}
                      {c.outcome || `${c.objectiveId} → ${c.choiceId}`}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {detailQuest.resolutionLog && detailQuest.resolutionLog.length > 0 ? (
              <div className="mt-2">
                <div className="text-xs uppercase text-ui-muted">Resolution log</div>
                <div className="mt-0.5 space-y-0.5">
                  {detailQuest.resolutionLog.slice(-8).map((row, idx) => (
                    <div key={`${row.objectiveId}:${row.completionKey}:${idx}`} className="text-xs text-ui-muted">
                      {row.at ? <span className="text-ui-soft">{new Date(row.at).toLocaleString()}: </span> : null}
                      {row.objectiveId ?? "?"} → {row.completionKey || "(step)"}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="mt-2 flex items-center gap-1">
              <TinyButton onClick={() => setDetailQuest(null)}>Close</TinyButton>
            </div>
          </div>
        </OverlayDialog>
      ) : null}
    </>
  );
}

function TinyButton({
  onClick,
  disabled,
  variant = "violet",
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  variant?: "cyan" | "pink" | "violet";
  children: React.ReactNode;
}) {
  const cls =
    variant === "pink"
      ? "shrink-0 rounded border border-pink-500/80 px-1 py-0 text-xs text-pink-400 hover:bg-pink-950/50 disabled:opacity-40"
      : variant === "cyan"
        ? "shrink-0 rounded border border-cyan-800/60 px-1 py-0 text-xs text-cyber-cyan hover:bg-cyan-900/40 disabled:opacity-40"
        : "shrink-0 rounded border border-violet-800/60 px-1 py-0 text-xs text-violet-300 hover:bg-violet-950/40 disabled:opacity-40";
  return (
    <button type="button" onClick={onClick} disabled={disabled} className={cls}>
      {children}
    </button>
  );
}

function OverlayDialog({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={title}>
      <button type="button" className="absolute inset-0 bg-zinc-950/70" aria-label="Close dialog" onClick={onClose} />
      <div className="absolute left-1/2 top-12 w-[min(520px,94vw)] -translate-x-1/2 rounded border border-violet-900/60 bg-zinc-950 p-2 text-xs text-foreground shadow-xl">
        <div className="mb-1 flex items-center gap-2 border-b border-zinc-800/60 pb-1">
          <div className="text-xs font-bold uppercase tracking-widest text-violet-300">{title}</div>
          <button type="button" className="ml-auto text-ui-muted hover:text-foreground" onClick={onClose}>
            ×
          </button>
        </div>
        <PipelineMatrixOverlay className="mt-1 min-h-[6rem] border border-violet-900/40 bg-black/25">
          {children}
        </PipelineMatrixOverlay>
      </div>
    </div>
  );
}
