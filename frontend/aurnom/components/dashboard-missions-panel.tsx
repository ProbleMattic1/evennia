"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { GameLogPanel } from "@/components/game-log-panel";
import type { MissionActive, MissionChoice, MissionOpportunity, MissionsState } from "@/lib/ui-api";
import { acceptMission, chooseMission, playInteract, playTravel } from "@/lib/ui-api";
import { useMsgStream } from "@/lib/use-msg-stream";

type Props = {
  missions: MissionsState;
  onChanged: () => void;
};

type ChoiceDialogState = {
  mission: MissionActive;
  choice: MissionChoice;
};

/**
 * Dashboard-styled missions panel with rich interactions (travel/interact/choice)
 * and dialog overlays for accepting opportunities and confirming choices.
 *
 * Intentionally does not reuse `components/mission-board.tsx` since it hardcodes
 * older visual styles (<details>, fuchsia palette, light buttons).
 */
export function DashboardMissionsPanel({ missions, onChanged }: Props) {
  const router = useRouter();
  const { messages: gameLog } = useMsgStream();

  const opportunities = missions.opportunities ?? [];
  const active = missions.active ?? [];
  const completed = missions.completed ?? [];

  const decisionsPending = useMemo(
    () => active.filter((m) => m.currentObjective?.kind === "choice").length,
    [active],
  );

  const storageKey = "aurnom:dashboard-panel:missions";
  const [open, setOpen] = useState(() => {
    if (typeof window === "undefined") return true;
    try {
      const raw = window.sessionStorage.getItem(storageKey);
      return raw == null ? true : raw === "1";
    } catch {
      return true;
    }
  });

  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  const [acceptOpp, setAcceptOpp] = useState<MissionOpportunity | null>(null);
  const [choiceDialog, setChoiceDialog] = useState<ChoiceDialogState | null>(null);
  const [detailMission, setDetailMission] = useState<MissionActive | null>(null);

  function toggleOpen() {
    setOpen((v) => {
      const next = !v;
      try {
        window.sessionStorage.setItem(storageKey, next ? "1" : "0");
      } catch {
        // ignore storage failures
      }
      return next;
    });
  }

  async function run(key: string, fn: () => Promise<{ message?: string }>) {
    if (busyKey) return;
    setBusyKey(key);
    setFlash(null);
    try {
      const res = await fn();
      setFlash(res.message ?? "OK");
      onChanged();
    } catch (e) {
      setFlash(e instanceof Error ? e.message : "Action failed");
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
    return key;
  }

  async function handleAccept(op: MissionOpportunity) {
    await run(`accept:${op.id}`, async () => acceptMission({ opportunityId: op.id }));
    setAcceptOpp(null);
  }

  async function handleChoose(m: MissionActive, c: MissionChoice) {
    await run(`choose:${m.id}:${c.id}`, async () => chooseMission({ missionId: m.id, choiceId: c.id }));
    setChoiceDialog(null);
  }

  async function handleTravel(m: MissionActive, roomKey: string) {
    await run(`travel:${m.id}:${roomKey}`, async () => playTravel({ destination: roomKey }));
    router.push("/");
    router.refresh();
  }

  async function handleInteract(m: MissionActive, interactionKey: string) {
    await run(`interact:${m.id}:${interactionKey}`, async () => playInteract({ interactionKey }));
    router.refresh();
  }

  return (
    <section className="mb-1">
      <div className="flex items-center bg-cyan-900/30 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-cyan-500">
        <span>{`Missions (${active.length} active / ${opportunities.length} avail)`}</span>
        <span className="ml-2 text-[9px] text-zinc-500">{`decisions pending: ${decisionsPending}`}</span>
        <button
          type="button"
          onClick={toggleOpen}
          aria-label={`${open ? "Collapse" : "Expand"} Missions`}
          className="ml-auto px-1 text-cyan-400 hover:text-cyan-300"
        >
          {open ? "▴" : "▸"}
        </button>
      </div>

      {open ? (
        <div className="border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-[11px]">
          {flash ? (
            <div className="mb-1 rounded border border-cyan-900/40 bg-zinc-950 px-1.5 py-1 text-[10px] text-zinc-300">
              <span className="text-cyan-400">»</span> {flash}
              <button type="button" className="ml-2 text-zinc-500 hover:text-zinc-300" onClick={() => setFlash(null)}>
                ×
              </button>
            </div>
          ) : null}

          <div className="mb-1.5">
            <div className="mb-0.5 text-[10px] uppercase tracking-wide text-zinc-500">Game log</div>
            <GameLogPanel messages={gameLog} compact />
          </div>

          <div className="space-y-1">
            {active.length > 0 ? (
              <div>
                <div className="text-[10px] uppercase text-zinc-500">Active</div>
                <div className="mt-0.5 space-y-1">
                  {active.map((m) => {
                    const obj = m.currentObjective ?? null;
                    const prompt = obj?.text ?? obj?.prompt ?? null;
                    const isChoice = obj?.kind === "choice" && (obj.choices?.length ?? 0) > 0;

                    return (
                      <div key={m.id} className="border-b border-zinc-800/60 pb-1 last:border-0 last:pb-0">
                        <div className="flex min-w-0 items-baseline gap-2">
                          <button
                            type="button"
                            className="min-w-0 truncate text-left font-semibold text-zinc-200 hover:text-cyan-300"
                            onClick={() => setDetailMission(m)}
                          >
                            {m.title}
                          </button>
                          <span className="ml-auto shrink-0 text-[9px] text-zinc-500">{m.status}</span>
                        </div>

                        {prompt ? <div className="mt-0.5 text-zinc-400">{prompt}</div> : null}

                        {obj?.kind === "visit_room" && (obj.roomKeysAny?.length ?? 0) > 0 ? (
                          <div className="mt-0.5 flex flex-wrap gap-1">
                            {obj.roomKeysAny!.map((roomKey) => {
                              const k = `travel:${m.id}:${roomKey}`;
                              return (
                                <TinyButton key={k} onClick={() => handleTravel(m, roomKey)} disabled={busyKey === k}>
                                  {busyKey === k ? "Traveling…" : `Go: ${roomKey}`}
                                </TinyButton>
                              );
                            })}
                          </div>
                        ) : null}

                        {obj?.kind === "interaction" && (obj.interactionKeysAny?.length ?? 0) > 0 ? (
                          <div className="mt-0.5 flex flex-wrap gap-1">
                            {obj.interactionKeysAny!.map((interactionKey) => {
                              const k = `interact:${m.id}:${interactionKey}`;
                              return (
                                <TinyButton
                                  key={k}
                                  onClick={() => handleInteract(m, interactionKey)}
                                  disabled={busyKey === k}
                                >
                                  {busyKey === k ? "Running…" : labelForInteractionKey(interactionKey)}
                                </TinyButton>
                              );
                            })}
                          </div>
                        ) : null}

                        {isChoice ? (
                          <div className="mt-0.5 flex flex-wrap gap-1">
                            {obj!.choices!.map((c) => (
                              <TinyButton key={`${m.id}:${c.id}`} onClick={() => setChoiceDialog({ mission: m, choice: c })}>
                                {c.label}
                              </TinyButton>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : null}

            {opportunities.length > 0 ? (
              <div>
                <div className="text-[10px] uppercase text-zinc-500">Available</div>
                <div className="mt-0.5 space-y-0.5">
                  {opportunities.map((op) => (
                    <div key={op.id} className="flex min-w-0 items-baseline gap-2">
                      <button
                        type="button"
                        className="min-w-0 flex-1 truncate text-left text-zinc-400 hover:text-cyan-300"
                        onClick={() => setAcceptOpp(op)}
                        title={op.summary}
                      >
                        {op.title}
                      </button>
                      <TinyButton onClick={() => setAcceptOpp(op)}>Accept…</TinyButton>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {completed.length > 0 ? (
              <div>
                <div className="text-[10px] uppercase text-zinc-500">{`Completed (${completed.length})`}</div>
                <div className="mt-0.5 space-y-0.5">
                  {completed.slice(-6).map((m) => (
                    <div key={m.id} className="flex min-w-0 items-baseline gap-2">
                      <span className="min-w-0 flex-1 truncate text-zinc-500">{m.title}</span>
                      {m.completedAt ? (
                        <span className="shrink-0 text-[9px] text-zinc-600">
                          {new Date(m.completedAt).toLocaleString()}
                        </span>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {active.length === 0 && opportunities.length === 0 ? <div className="text-zinc-500">No missions available.</div> : null}
          </div>
        </div>
      ) : null}

      {acceptOpp ? (
        <OverlayDialog title="Accept mission" onClose={() => setAcceptOpp(null)}>
          <div className="space-y-1">
            <div className="text-[12px] font-semibold text-zinc-200">{acceptOpp.title}</div>
            <div className="text-zinc-400">{acceptOpp.summary}</div>

            <div className="mt-2 flex items-center gap-1">
              <TinyButton
                onClick={() => handleAccept(acceptOpp)}
                disabled={busyKey === `accept:${acceptOpp.id}`}
              >
                {busyKey === `accept:${acceptOpp.id}` ? "Accepting…" : "Confirm accept"}
              </TinyButton>
              <TinyButton onClick={() => setAcceptOpp(null)}>Cancel</TinyButton>
            </div>
          </div>
        </OverlayDialog>
      ) : null}

      {choiceDialog ? (
        <OverlayDialog title="Decide" onClose={() => setChoiceDialog(null)}>
          <div className="space-y-1">
            <div className="text-[12px] font-semibold text-zinc-200">{choiceDialog.mission.title}</div>
            <div className="text-zinc-400">
              {choiceDialog.mission.currentObjective?.prompt ?? choiceDialog.mission.currentObjective?.text}
            </div>

            <div className="mt-2 rounded border border-cyan-900/40 bg-zinc-950 p-1.5">
              <div className="text-[10px] uppercase tracking-wide text-zinc-500">Choice</div>
              <div className="text-zinc-200">{choiceDialog.choice.label}</div>

              {choiceDialog.choice.outcome ? (
                <div className="mt-1 text-zinc-400">
                  <span className="text-zinc-500">Outcome:</span> {choiceDialog.choice.outcome}
                </div>
              ) : null}

              {choiceDialog.choice.morality ? (
                <div className="mt-1 text-[10px] text-zinc-500">{formatMoralityDelta(choiceDialog.choice.morality)}</div>
              ) : null}

              {choiceDialog.choice.rewards ? (
                <div className="mt-1 text-[10px] text-zinc-500">{formatRewards(choiceDialog.choice.rewards)}</div>
              ) : null}
            </div>

            <div className="mt-2 flex items-center gap-1">
              <TinyButton
                onClick={() => handleChoose(choiceDialog.mission, choiceDialog.choice)}
                disabled={busyKey === `choose:${choiceDialog.mission.id}:${choiceDialog.choice.id}`}
              >
                {busyKey === `choose:${choiceDialog.mission.id}:${choiceDialog.choice.id}` ? "Submitting…" : "Confirm"}
              </TinyButton>
              <TinyButton onClick={() => setChoiceDialog(null)}>Cancel</TinyButton>
            </div>
          </div>
        </OverlayDialog>
      ) : null}

      {detailMission ? (
        <OverlayDialog title="Mission detail" onClose={() => setDetailMission(null)}>
          <div className="space-y-1">
            <div className="text-[12px] font-semibold text-zinc-200">{detailMission.title}</div>
            {detailMission.summary ? <div className="text-zinc-400">{detailMission.summary}</div> : null}

            {detailMission.choices && detailMission.choices.length > 0 ? (
              <div className="mt-2">
                <div className="text-[10px] uppercase text-zinc-500">History</div>
                <div className="mt-0.5 space-y-0.5">
                  {detailMission.choices.slice(-6).map((c, idx) => (
                    <div key={`${c.objectiveId}:${c.choiceId}:${idx}`} className="text-[10px] text-zinc-500">
                      <span className="text-zinc-400">{new Date(c.chosenAt).toLocaleString()}:</span>{" "}
                      {c.outcome || `${c.objectiveId} → ${c.choiceId}`}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="mt-2 flex items-center gap-1">
              <TinyButton onClick={() => setDetailMission(null)}>Close</TinyButton>
            </div>
          </div>
        </OverlayDialog>
      ) : null}
    </section>
  );
}

function TinyButton({
  onClick,
  disabled,
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="shrink-0 rounded border border-cyan-800/60 px-1 py-0 text-[10px] text-cyan-400 hover:bg-cyan-900/40 disabled:opacity-40"
    >
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
      <div className="absolute left-1/2 top-12 w-[min(520px,94vw)] -translate-x-1/2 rounded border border-cyan-900/60 bg-zinc-950 p-2 text-[11px] text-zinc-300 shadow-xl">
        <div className="mb-1 flex items-center gap-2 border-b border-zinc-800/60 pb-1">
          <div className="text-[10px] font-bold uppercase tracking-widest text-cyan-400">{title}</div>
          <button type="button" className="ml-auto text-zinc-500 hover:text-zinc-300" onClick={onClose}>
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function formatMoralityDelta(delta: Record<string, unknown>) {
  const parts: string[] = [];
  for (const k of ["good", "evil", "lawful", "chaotic"] as const) {
    const v = Number(delta[k] ?? 0);
    if (!v) continue;
    parts.push(`${k} ${v > 0 ? `+${v}` : String(v)}`);
  }
  return parts.length ? `Morality: ${parts.join(" · ")}` : "";
}

function formatRewards(rewards: Record<string, unknown>) {
  const parts: string[] = [];
  for (const [k, v] of Object.entries(rewards)) {
    if (v == null) continue;
    parts.push(`${k}: ${String(v)}`);
  }
  return parts.length ? `Rewards: ${parts.join(" · ")}` : "";
}
