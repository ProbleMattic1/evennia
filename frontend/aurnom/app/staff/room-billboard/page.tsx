"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import type { BillboardLibraryPreset, StaffBillboardCatalog } from "@/lib/ui-api";
import { getStaffBillboardState, postStaffBillboardApply } from "@/lib/ui-api";

type SlidePick = "__default__" | "__none__" | string;

function slidePickValue(
  slideId: string,
  _preset: BillboardLibraryPreset,
  selection: Record<string, string | null | undefined> | undefined,
): SlidePick {
  if (selection && Object.prototype.hasOwnProperty.call(selection, slideId)) {
    const v = selection[slideId];
    if (v === null) return "__none__";
    if (typeof v === "string" && v) return v;
    return "__none__";
  }
  return "__default__";
}

export default function StaffRoomBillboardPage() {
  const [catalog, setCatalog] = useState<StaffBillboardCatalog | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [roomKey, setRoomKey] = useState("");
  const [presetId, setPresetId] = useState("");
  const [styleId, setStyleId] = useState("");
  const [slidePicks, setSlidePicks] = useState<Record<string, SlidePick>>({});
  const [roomErr, setRoomErr] = useState<string | null>(null);
  const [applyErr, setApplyErr] = useState<string | null>(null);
  const [applyOk, setApplyOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const activePreset = useMemo(
    () => catalog?.presets.find((p) => p.id === presetId) ?? null,
    [catalog, presetId],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getStaffBillboardState();
        if (cancelled) return;
        setCatalog(data.catalog);
        setLoadErr(null);
        const firstRoom = data.catalog.rooms[0] ?? "";
        setRoomKey(firstRoom);
      } catch (e) {
        if (!cancelled) {
          setLoadErr(e instanceof Error ? e.message : "Failed to load catalog.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const refreshRoom = useCallback(async (rk: string) => {
    if (!rk) {
      setRoomErr(null);
      return;
    }
    setRoomErr(null);
    try {
      const data = await getStaffBillboardState(rk);
      const sel = data.billboardSelection;
      const pid = sel?.presetId && data.catalog.presets.some((p) => p.id === sel.presetId) ? sel.presetId : data.catalog.presets[0]?.id ?? "";
      const sid = sel?.styleId && data.catalog.styles.some((s) => s.id === sel.styleId) ? sel.styleId : data.catalog.styles[0]?.id ?? "";
      setPresetId(pid);
      setStyleId(sid);
      const preset = data.catalog.presets.find((p) => p.id === pid);
      const next: Record<string, SlidePick> = {};
      if (preset) {
        for (const s of preset.bannerSlides) {
          next[s.id] = slidePickValue(s.id, preset, sel?.slideImages);
        }
      }
      setSlidePicks(next);
    } catch (e) {
      setRoomErr(e instanceof Error ? e.message : "Failed to load room.");
    }
  }, []);

  useEffect(() => {
    if (!catalog || !roomKey) return;
    void refreshRoom(roomKey);
  }, [catalog, roomKey, refreshRoom]);

  const setPick = (slideId: string, v: SlidePick) => {
    setSlidePicks((p) => ({ ...p, [slideId]: v }));
  };

  const handleApply = async () => {
    setApplyErr(null);
    setApplyOk(null);
    if (!roomKey || !presetId || !styleId || !activePreset) {
      setApplyErr("Choose a room, preset, and style.");
      return;
    }
    const slideImages: Record<string, string | null> = {};
    for (const s of activePreset.bannerSlides) {
      const pick = slidePicks[s.id] ?? "__default__";
      const presetDefault = s.imageKey?.trim() ?? null;
      if (pick === "__default__") continue;
      if (pick === "__none__") {
        slideImages[s.id] = null;
        continue;
      }
      if (pick === presetDefault) continue;
      slideImages[s.id] = pick;
    }
    setBusy(true);
    try {
      await postStaffBillboardApply({
        roomKey,
        presetId,
        styleId,
        slideImages: Object.keys(slideImages).length ? slideImages : undefined,
      });
      setApplyOk("Applied.");
      await refreshRoom(roomKey);
    } catch (e) {
      setApplyErr(e instanceof Error ? e.message : "Apply failed.");
    } finally {
      setBusy(false);
    }
  };

  if (loadErr) {
    return (
      <CsPage>
        <CsHeader title="Room billboard" subtitle="Staff only" />
        <p className="px-2 py-3 text-sm text-red-600 dark:text-red-400">{loadErr}</p>
      </CsPage>
    );
  }

  if (!catalog) {
    return (
      <CsPage>
        <CsHeader title="Room billboard" subtitle="Staff only" />
        <p className="px-2 py-3 text-sm text-ui-muted">Loading…</p>
      </CsPage>
    );
  }

  return (
    <CsPage>
      <CsHeader title="Room billboard" subtitle="Staff only — selections only; copy and assets come from billboard_library.json" />

      <CsPanel title="Assignment">
        {roomErr ? <p className="mb-2 text-sm text-red-600 dark:text-red-400">{roomErr}</p> : null}
        {applyErr ? <p className="mb-2 text-sm text-red-600 dark:text-red-400">{applyErr}</p> : null}
        {applyOk ? <p className="mb-2 text-sm text-ui-accent-readable">{applyOk}</p> : null}

        <div className="mt-2 grid gap-3 text-sm">
          <label className="grid gap-1">
            <span className="text-ui-muted">Room</span>
            <select
              className="rounded border border-cyan-900/50 bg-zinc-950 px-2 py-1.5 font-mono text-foreground"
              value={roomKey}
              onChange={(e) => setRoomKey(e.target.value)}
            >
              {catalog.rooms.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>

          <label className="grid gap-1">
            <span className="text-ui-muted">Preset</span>
            <select
              className="rounded border border-cyan-900/50 bg-zinc-950 px-2 py-1.5 font-mono text-foreground"
              value={presetId}
              onChange={(e) => {
                const id = e.target.value;
                setPresetId(id);
                const p = catalog.presets.find((x) => x.id === id);
                if (p) {
                  const next: Record<string, SlidePick> = {};
                  for (const s of p.bannerSlides) {
                    next[s.id] = s.imageKey?.trim() ? s.imageKey.trim() : "__default__";
                  }
                  setSlidePicks(next);
                }
              }}
            >
              {catalog.presets.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id}
                </option>
              ))}
            </select>
          </label>

          <label className="grid gap-1">
            <span className="text-ui-muted">Style</span>
            <select
              className="rounded border border-cyan-900/50 bg-zinc-950 px-2 py-1.5 font-mono text-foreground"
              value={styleId}
              onChange={(e) => setStyleId(e.target.value)}
            >
              {catalog.styles.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.id} ({s.themeId}, {s.marqueeClass})
                </option>
              ))}
            </select>
          </label>

          {activePreset ? (
            <div className="grid gap-2 border-t border-cyan-900/30 pt-3">
              <span className="text-ui-muted">Slide image (from /public/billboards/)</span>
              {activePreset.bannerSlides.map((s) => (
                <label key={s.id} className="grid gap-1">
                  <span className="font-mono text-xs text-ui-muted">{s.id}</span>
                  <select
                    className="rounded border border-cyan-900/50 bg-zinc-950 px-2 py-1.5 font-mono text-foreground"
                    value={slidePicks[s.id] ?? "__default__"}
                    onChange={(e) => setPick(s.id, e.target.value as SlidePick)}
                  >
                    <option value="__default__">Preset default</option>
                    <option value="__none__">No image</option>
                    {catalog.images.map((img) => (
                      <option key={img} value={img}>
                        {img}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          ) : null}

          <button
            type="button"
            disabled={busy || !roomKey}
            className="rounded border border-cyan-800/60 px-2 py-1.5 text-xs text-cyber-cyan hover:bg-cyan-900/40 disabled:opacity-50"
            onClick={() => void handleApply()}
          >
            {busy ? "Applying…" : "Apply to room"}
          </button>
        </div>
      </CsPanel>
    </CsPage>
  );
}
