"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { CsButtonLink, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import type { MailMessageSummary, MailScope } from "@/lib/ui-api";
import { getMailState, postMailDelete, postMailSend } from "@/lib/ui-api";

export default function MailPage() {
  const [scope, setScope] = useState<MailScope>("account");
  const [rows, setRows] = useState<MailMessageSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detailBody, setDetailBody] = useState<string | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [recipients, setRecipients] = useState("");
  const [subject, setSubject] = useState("");
  const [composeBody, setComposeBody] = useState("");
  const [sendErr, setSendErr] = useState<string | null>(null);
  const [sendOk, setSendOk] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoadErr(null);
    setBusy(true);
    try {
      const data = await getMailState({
        scope,
        fullMessageId: selectedId ?? undefined,
      });
      setRows(data.messages);
      if (data.selectedMessage) {
        setDetailBody(data.selectedMessage.body);
      } else if (selectedId == null) {
        setDetailBody(null);
      }
    } catch (e) {
      setLoadErr(e instanceof Error ? e.message : String(e));
      setRows([]);
      setDetailBody(null);
    } finally {
      setBusy(false);
    }
  }, [scope, selectedId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const selectedRow = useMemo(() => rows.find((r) => r.id === selectedId) ?? null, [rows, selectedId]);

  async function onDelete(id: number) {
    setSendErr(null);
    setSendOk(null);
    setBusy(true);
    try {
      await postMailDelete({ scope, messageId: id });
      if (selectedId === id) {
        setSelectedId(null);
        setDetailBody(null);
      }
      await reload();
    } catch (e) {
      setSendErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onSend(e: React.FormEvent) {
    e.preventDefault();
    setSendErr(null);
    setSendOk(null);
    const names = recipients
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!names.length) {
      setSendErr("Enter at least one recipient (comma-separated account names or character keys).");
      return;
    }
    setBusy(true);
    try {
      const out = await postMailSend({
        scope,
        recipientNames: names,
        subject,
        body: composeBody,
      });
      setSendOk(out.message);
      setRecipients("");
      setSubject("");
      setComposeBody("");
      await reload();
    } catch (err) {
      setSendErr(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <CsPage>
      <CsHeader
        title="@mail"
        subtitle={
          scope === "account"
            ? "Account mailbox (OOC-style; same targets as the account mail command)."
            : "Character mailbox (IC mail to other characters; requires a resolved web character)."
        }
        actions={<CsButtonLink href="/">Back</CsButtonLink>}
      />

      <div className="mb-2 flex flex-wrap gap-2 text-xs">
        <span className="text-ui-muted">Scope:</span>
        {(["account", "character"] as const).map((s) => (
          <button
            key={s}
            type="button"
            disabled={busy}
            onClick={() => {
              setSelectedId(null);
              setDetailBody(null);
              setScope(s);
            }}
            className={`rounded border px-2 py-0.5 uppercase tracking-wide ${
              scope === s ? "border-cyber-cyan text-cyber-cyan" : "border-cyan-900/50 text-ui-muted"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {loadErr ? <p className="mb-2 text-sm text-red-600 dark:text-red-400">{loadErr}</p> : null}

      <div className="grid gap-2 md:grid-cols-2">
        <CsPanel title="Inbox">
          {rows.length === 0 ? (
            <p className="text-sm text-ui-muted">No messages.</p>
          ) : (
            <ul className="max-h-[22rem] space-y-1 overflow-y-auto text-xs">
              {rows.map((m) => (
                <li key={m.id}>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => setSelectedId(m.id)}
                    className={`w-full rounded border px-1.5 py-1 text-left ${
                      selectedId === m.id ? "border-cyber-cyan bg-cyan-950/30" : "border-cyan-900/40"
                    }`}
                  >
                    <span className="font-mono text-ui-muted">{m.dateCreated ?? "—"}</span>
                    {m.hasNewTag ? <span className="ml-1 text-amber-400">new</span> : null}
                    <div className="truncate font-semibold text-foreground">{m.header || "(no subject)"}</div>
                    <div className="truncate text-ui-muted">From {m.sender}</div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CsPanel>

        <CsPanel title={selectedRow ? selectedRow.header || "Message" : "Open a message"}>
          {selectedRow ? (
            <div className="space-y-2 text-sm">
              <p className="text-ui-muted">
                {selectedRow.dateCreated ?? "—"} · from {selectedRow.sender}
              </p>
              <pre className="whitespace-pre-wrap break-words font-sans text-foreground">{detailBody ?? "…"}</pre>
              <button
                type="button"
                disabled={busy}
                onClick={() => void onDelete(selectedRow.id)}
                className="rounded border border-red-900/60 px-2 py-1 text-xs text-red-400"
              >
                Delete
              </button>
            </div>
          ) : (
            <p className="text-sm text-ui-muted">Select a row to read the full body.</p>
          )}
        </CsPanel>
      </div>

      <CsPanel title="Compose" className="mt-2">
        <form onSubmit={onSend} className="space-y-2 text-sm">
          <label className="block">
            <span className="text-ui-muted">Recipients (comma-separated)</span>
            <input
              value={recipients}
              onChange={(e) => setRecipients(e.target.value)}
              className="mt-0.5 w-full rounded border border-cyan-900/50 bg-zinc-950 px-2 py-1 font-mono text-xs"
              placeholder={scope === "account" ? "player1, player2" : "SomeCharacter, OtherCharacter"}
            />
          </label>
          <label className="block">
            <span className="text-ui-muted">Subject</span>
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="mt-0.5 w-full rounded border border-cyan-900/50 bg-zinc-950 px-2 py-1 font-mono text-xs"
            />
          </label>
          <label className="block">
            <span className="text-ui-muted">Body</span>
            <textarea
              value={composeBody}
              onChange={(e) => setComposeBody(e.target.value)}
              rows={5}
              className="mt-0.5 w-full rounded border border-cyan-900/50 bg-zinc-950 px-2 py-1 font-mono text-xs"
            />
          </label>
          {sendErr ? <p className="text-red-600 dark:text-red-400">{sendErr}</p> : null}
          {sendOk ? <p className="text-emerald-500">{sendOk}</p> : null}
          <button
            type="submit"
            disabled={busy}
            className="rounded border border-cyber-cyan px-3 py-1 text-xs font-bold uppercase tracking-wide text-cyber-cyan"
          >
            Send
          </button>
        </form>
      </CsPanel>
    </CsPage>
  );
}
