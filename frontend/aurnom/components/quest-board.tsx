"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { acceptQuest, chooseQuest, playInteract, playTravel, webNavigatePathFromPlayResult } from "@/lib/ui-api";
import type { QuestObjective, QuestResolvePath, QuestsState } from "@/lib/ui-api";

type Props = {
  quests: QuestsState;
  onChanged: () => void;
};

function interactionKeysFromResolvePaths(paths: QuestResolvePath[] | undefined): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const p of paths ?? []) {
    if (p.via !== "interaction") continue;
    for (const k of p.interactionKeysAny ?? []) {
      const low = k.trim().toLowerCase();
      if (!low || seen.has(low)) continue;
      seen.add(low);
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

export function QuestBoard({ quests, onChanged }: Props) {
  const router = useRouter();
  const [pendingAccept, setPendingAccept] = useState<string | null>(null);
  const [pendingChoose, setPendingChoose] = useState<string | null>(null);
  const [pendingPathAction, setPendingPathAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const opportunities = quests.opportunities ?? [];
  const active = quests.active ?? [];
  const completed = quests.completed ?? [];

  const decisionsPending = useMemo(
    () => active.filter((q) => q.currentObjective?.kind === "choice").length,
    [active],
  );

  async function handleAccept(opportunityId: string) {
    setError(null);
    setNotice(null);
    setPendingAccept(opportunityId);
    try {
      const res = await acceptQuest({ opportunityId });
      setNotice(res.message ?? "Quest accepted.");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Quest accept failed.");
    } finally {
      setPendingAccept(null);
    }
  }

  async function handleChoose(questId: string, choiceId: string) {
    const pendingKey = `${questId}:${choiceId}`;
    setError(null);
    setNotice(null);
    setPendingChoose(pendingKey);
    try {
      const res = await chooseQuest({ questId, choiceId });
      setNotice(res.message ?? "Choice recorded.");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Quest choice failed.");
    } finally {
      setPendingChoose(null);
    }
  }

  function labelForInteractionKey(key: string): string {
    if (key.startsWith("askguide")) {
      const topic = key.split(":")[1];
      return `Ask guide (${topic ?? "default"})`;
    }
    if (key === "survey") {
      return "Run survey";
    }
    if (key === "contractboard") {
      return "Procurement board";
    }
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

  async function handleVisitRoom(questId: string, roomKey: string) {
    const pendingKey = `travel:${questId}:${roomKey}`;
    setError(null);
    setNotice(null);
    setPendingPathAction(pendingKey);
    try {
      const res = await playTravel({ destination: roomKey });
      setNotice(res.message ?? `Moved to ${roomKey}.`);
      router.push(webNavigatePathFromPlayResult(res));
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Travel failed.");
    } finally {
      setPendingPathAction(null);
    }
  }

  async function handleInteraction(questId: string, interactionKey: string) {
    const pendingKey = `interact:${questId}:${interactionKey}`;
    setError(null);
    setNotice(null);
    setPendingPathAction(pendingKey);
    try {
      const res = await playInteract({ interactionKey });
      setNotice(res.message ?? "Interaction executed.");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Interaction failed.");
    } finally {
      setPendingPathAction(null);
    }
  }

  function renderObjectiveBlock(questId: string, objective: QuestObjective) {
    return (
      <div className="mt-1 rounded border border-violet-900/40 bg-zinc-900/50 px-2 py-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-ui-soft">Next step</p>

        {objective.kind === "visit_room" && (objective.roomKeysAny?.length ?? 0) > 0 ? (
          <div className="mt-1 flex flex-wrap gap-1">
            {objective.roomKeysAny?.map((roomKey) => {
              const busyKey = `travel:${questId}:${roomKey}`;
              return (
                <button
                  key={roomKey}
                  type="button"
                  onClick={() => handleVisitRoom(questId, roomKey)}
                  disabled={pendingPathAction === busyKey}
                  className="rounded border border-zinc-300 px-2 py-0.5 text-xs hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                >
                  {pendingPathAction === busyKey ? "Traveling..." : `Go to ${roomKey}`}
                </button>
              );
            })}
          </div>
        ) : null}

        {objective.kind === "interaction" && (objective.interactionKeysAny?.length ?? 0) > 0 ? (
          <div className="mt-1 flex flex-wrap gap-1">
            {objective.interactionKeysAny?.map((interactionKey) => {
              const busyKey = `interact:${questId}:${interactionKey}`;
              return (
                <button
                  key={interactionKey}
                  type="button"
                  onClick={() => handleInteraction(questId, interactionKey)}
                  disabled={pendingPathAction === busyKey}
                  className="rounded border border-zinc-300 px-2 py-0.5 text-xs hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                >
                  {pendingPathAction === busyKey ? "Running..." : labelForInteractionKey(interactionKey)}
                </button>
              );
            })}
          </div>
        ) : null}

        {objective.kind === "resolve_situation" ? (
          <div className="mt-1 space-y-1">
            <p className="text-xs text-ui-muted">
              Win the matching combat encounter or use an interaction below.
            </p>
            {signalHintsFromResolvePaths(objective.paths).map((h) => (
              <p key={h} className="text-xs text-ui-soft">
                Combat: {h}
              </p>
            ))}
            <div className="flex flex-wrap gap-1">
              {interactionKeysFromResolvePaths(objective.paths).map((interactionKey) => {
                const busyKey = `interact:${questId}:${interactionKey}`;
                return (
                  <button
                    key={interactionKey}
                    type="button"
                    onClick={() => handleInteraction(questId, interactionKey)}
                    disabled={pendingPathAction === busyKey}
                    className="rounded border border-zinc-300 px-2 py-0.5 text-xs hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                  >
                    {pendingPathAction === busyKey ? "Running..." : labelForInteractionKey(interactionKey)}
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

        {objective.kind === "choice" ? (
          <p className="mt-1 text-xs text-ui-muted">Choose one option below to proceed.</p>
        ) : null}
      </div>
    );
  }

  return (
    <section className="mx-2 rounded-lg border border-violet-200/60 bg-violet-50/40 px-3 py-2 dark:border-violet-800/40 dark:bg-violet-950/20">
      <details className="group" open>
        <summary className="flex cursor-pointer list-none items-center justify-between text-xs font-bold uppercase tracking-widest text-violet-300 [&::-webkit-details-marker]:hidden">
          <span>Main quest board</span>
          <svg
            className="size-3 shrink-0 transition-transform group-open:rotate-90"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </summary>
        <div className="mt-1">
          <p className="text-xs text-ui-accent-readable">
            Opportunities: {opportunities.length} · Active: {active.length} · Decisions pending: {decisionsPending}
          </p>

          {error ? <p className="mt-2 text-xs text-red-600 dark:text-red-400">{error}</p> : null}
          {notice ? <p className="mt-2 text-xs text-emerald-600 dark:text-emerald-400">{notice}</p> : null}

          <details className="group mt-2" open>
            <summary className="cursor-pointer list-none text-xs font-bold uppercase tracking-widest text-violet-300 [&::-webkit-details-marker]:hidden">
              Opportunities
            </summary>
            {opportunities.length === 0 ? (
              <p className="mt-1 text-xs text-ui-muted">No quest opportunities right now.</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {opportunities.map((op) => (
                  <li key={op.id} className="rounded bg-white/50 px-2 py-1 dark:bg-zinc-900/20">
                    <p className="text-sm font-medium text-zinc-800 dark:text-foreground">{op.title}</p>
                    <p className="text-xs text-ui-muted">{op.summary}</p>
                    <button
                      type="button"
                      onClick={() => handleAccept(op.id)}
                      disabled={pendingAccept === op.id}
                      className="mt-1 rounded border border-zinc-300 px-2 py-0.5 text-xs hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                    >
                      {pendingAccept === op.id ? "Accepting..." : "Accept"}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </details>

          <details className="group mt-2" open>
            <summary className="cursor-pointer list-none text-xs font-bold uppercase tracking-widest text-violet-300 [&::-webkit-details-marker]:hidden">
              Active
            </summary>
            {active.length === 0 ? (
              <p className="mt-1 text-xs text-ui-muted">No active quests.</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {active.map((q) => {
                  const objective = q.currentObjective;
                  return (
                    <li key={q.id} className="rounded bg-white/50 px-2 py-1 dark:bg-zinc-900/20">
                      <p className="text-sm font-medium text-zinc-800 dark:text-foreground">{q.title}</p>
                      {objective?.prompt || objective?.text ? (
                        <p className="text-xs text-ui-muted">{objective.prompt ?? objective.text}</p>
                      ) : null}
                      {objective ? renderObjectiveBlock(q.id, objective) : null}
                      {objective?.kind === "choice" && (objective.choices?.length ?? 0) > 0 ? (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {objective.choices?.map((choice) => {
                            const key = `${q.id}:${choice.id}`;
                            return (
                              <button
                                key={choice.id}
                                type="button"
                                onClick={() => handleChoose(q.id, choice.id)}
                                disabled={pendingChoose === key}
                                className="rounded border border-zinc-300 px-2 py-0.5 text-xs hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                              >
                                {pendingChoose === key ? "Submitting..." : choice.label}
                              </button>
                            );
                          })}
                        </div>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            )}
          </details>

          <details className="group mt-2">
            <summary className="cursor-pointer list-none text-xs font-bold uppercase tracking-widest text-violet-300 [&::-webkit-details-marker]:hidden">
              Completed ({completed.length})
            </summary>
            {completed.length === 0 ? (
              <p className="mt-1 text-xs text-ui-muted">No completed quests yet.</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {completed.map((q) => (
                  <li key={q.id} className="rounded bg-white/50 px-2 py-1 text-xs dark:bg-zinc-900/20">
                    <span className="font-medium text-zinc-800 dark:text-foreground">{q.title}</span>
                    {q.completedAt ? (
                      <span className="ml-2 text-ui-muted">{new Date(q.completedAt).toLocaleString()}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </details>
        </div>
      </details>
    </section>
  );
}
