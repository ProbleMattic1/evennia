"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { acceptMission, chooseMission, playInteract, playTravel } from "@/lib/ui-api";
import type { MissionsState } from "@/lib/ui-api";

type Props = {
  missions: MissionsState;
  onChanged: () => void;
};

export function MissionBoard({ missions, onChanged }: Props) {
  const router = useRouter();
  const [pendingAccept, setPendingAccept] = useState<string | null>(null);
  const [pendingChoose, setPendingChoose] = useState<string | null>(null);
  const [pendingPathAction, setPendingPathAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const morality = missions.morality ?? { good: 0, evil: 0, lawful: 0, chaotic: 0 };
  const opportunities = missions.opportunities ?? [];
  const active = missions.active ?? [];
  const completed = missions.completed ?? [];

  const decisionsPending = useMemo(
    () => active.filter((m) => m.currentObjective?.kind === "choice").length,
    [active]
  );

  async function handleAccept(opportunityId: string) {
    setError(null);
    setNotice(null);
    setPendingAccept(opportunityId);
    try {
      const res = await acceptMission({ opportunityId });
      setNotice(res.message ?? "Mission accepted.");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mission accept failed.");
    } finally {
      setPendingAccept(null);
    }
  }

  async function handleChoose(missionId: string, choiceId: string) {
    const pendingKey = `${missionId}:${choiceId}`;
    setError(null);
    setNotice(null);
    setPendingChoose(pendingKey);
    try {
      const res = await chooseMission({ missionId, choiceId });
      setNotice(res.message ?? "Choice recorded.");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mission choice failed.");
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
    return key;
  }

  async function handleVisitRoom(missionId: string, roomKey: string) {
    const pendingKey = `travel:${missionId}:${roomKey}`;
    setError(null);
    setNotice(null);
    setPendingPathAction(pendingKey);
    try {
      const res = await playTravel({ destination: roomKey });
      setNotice(res.message ?? `Moved to ${roomKey}.`);
      router.push("/");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Travel failed.");
    } finally {
      setPendingPathAction(null);
    }
  }

  async function handleInteraction(missionId: string, interactionKey: string) {
    const pendingKey = `interact:${missionId}:${interactionKey}`;
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

  return (
    <section className="mx-2 rounded-lg border border-fuchsia-200/60 bg-fuchsia-50/40 px-3 py-2 dark:border-fuchsia-800/40 dark:bg-fuchsia-950/20">
      <details className="group" open>
        <summary className="flex cursor-pointer list-none items-center justify-between text-[10px] font-bold uppercase tracking-widest text-cyan-300 [&::-webkit-details-marker]:hidden">
          <span>Mission Board</span>
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
          <p className="text-[12px] text-ui-accent-readable">
            Opportunities: {opportunities.length} · Active: {active.length} · Decisions pending: {decisionsPending}
          </p>

          <div className="mt-1 flex flex-wrap gap-1.5 text-[11px]">
            <span className="rounded bg-emerald-100 px-1.5 py-0.5 dark:bg-emerald-900/40">Good {morality.good}</span>
            <span className="rounded bg-red-100 px-1.5 py-0.5 dark:bg-red-900/40">Evil {morality.evil}</span>
            <span className="rounded bg-sky-100 px-1.5 py-0.5 dark:bg-sky-900/40">Lawful {morality.lawful}</span>
            <span className="rounded bg-amber-100 px-1.5 py-0.5 dark:bg-amber-900/40">Chaotic {morality.chaotic}</span>
          </div>

          {error ? <p className="mt-2 text-[12px] text-red-600 dark:text-red-400">{error}</p> : null}
          {notice ? <p className="mt-2 text-[12px] text-emerald-600 dark:text-emerald-400">{notice}</p> : null}

          <details className="group mt-2" open>
            <summary className="cursor-pointer list-none text-[10px] font-bold uppercase tracking-widest text-cyan-300 [&::-webkit-details-marker]:hidden">
              Opportunities
            </summary>
            {opportunities.length === 0 ? (
              <p className="mt-1 text-[12px] text-ui-muted">No mission opportunities right now.</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {opportunities.map((op) => (
                  <li key={op.id} className="rounded bg-white/50 px-2 py-1 dark:bg-zinc-900/20">
                    <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">{op.title}</p>
                    <p className="text-[12px] text-ui-muted">{op.summary}</p>
                    <button
                      type="button"
                      onClick={() => handleAccept(op.id)}
                      disabled={pendingAccept === op.id}
                      className="mt-1 rounded border border-zinc-300 px-2 py-0.5 text-[12px] hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                    >
                      {pendingAccept === op.id ? "Accepting..." : "Accept"}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </details>

          <details className="group mt-2" open>
            <summary className="cursor-pointer list-none text-[10px] font-bold uppercase tracking-widest text-cyan-300 [&::-webkit-details-marker]:hidden">
              Active
            </summary>
            {active.length === 0 ? (
              <p className="mt-1 text-[12px] text-ui-muted">No active missions.</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {active.map((m) => {
                  const objective = m.currentObjective;
                  return (
                    <li key={m.id} className="rounded bg-white/50 px-2 py-1 dark:bg-zinc-900/20">
                      <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">{m.title}</p>
                      {objective?.prompt || objective?.text ? (
                        <p className="text-[12px] text-ui-muted">
                          {objective.prompt ?? objective.text}
                        </p>
                      ) : null}
                      {objective ? (
                        <div className="mt-1 rounded border border-cyan-900/40 bg-zinc-900/50 px-2 py-1">
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-ui-soft">
                            Next step
                          </p>

                          {objective.kind === "visit_room" && (objective.roomKeysAny?.length ?? 0) > 0 ? (
                            <div className="mt-1 flex flex-wrap gap-1">
                              {objective.roomKeysAny?.map((roomKey) => {
                                const busyKey = `travel:${m.id}:${roomKey}`;
                                return (
                                  <button
                                    key={roomKey}
                                    type="button"
                                    onClick={() => handleVisitRoom(m.id, roomKey)}
                                    disabled={pendingPathAction === busyKey}
                                    className="rounded border border-zinc-300 px-2 py-0.5 text-[12px] hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
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
                                const busyKey = `interact:${m.id}:${interactionKey}`;
                                return (
                                  <button
                                    key={interactionKey}
                                    type="button"
                                    onClick={() => handleInteraction(m.id, interactionKey)}
                                    disabled={pendingPathAction === busyKey}
                                    className="rounded border border-zinc-300 px-2 py-0.5 text-[12px] hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                                  >
                                    {pendingPathAction === busyKey
                                      ? "Running..."
                                      : labelForInteractionKey(interactionKey)}
                                  </button>
                                );
                              })}
                            </div>
                          ) : null}

                          {objective.kind === "choice" ? (
                            <p className="mt-1 text-[12px] text-ui-muted">
                              Choose one option below to proceed.
                            </p>
                          ) : null}
                        </div>
                      ) : null}
                      {objective?.kind === "choice" && (objective.choices?.length ?? 0) > 0 ? (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {objective.choices?.map((choice) => {
                            const key = `${m.id}:${choice.id}`;
                            return (
                              <button
                                key={choice.id}
                                type="button"
                                onClick={() => handleChoose(m.id, choice.id)}
                                disabled={pendingChoose === key}
                                className="rounded border border-zinc-300 px-2 py-0.5 text-[12px] hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
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
            <summary className="cursor-pointer list-none text-[10px] font-bold uppercase tracking-widest text-cyan-300 [&::-webkit-details-marker]:hidden">
              Completed ({completed.length})
            </summary>
            {completed.length === 0 ? (
              <p className="mt-1 text-[12px] text-ui-muted">No completed missions yet.</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {completed.map((m) => (
                  <li key={m.id} className="rounded bg-white/50 px-2 py-1 text-[12px] dark:bg-zinc-900/20">
                    <span className="font-medium text-zinc-800 dark:text-zinc-200">{m.title}</span>
                    {m.completedAt ? (
                      <span className="ml-2 text-ui-muted">
                        {new Date(m.completedAt).toLocaleString()}
                      </span>
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
