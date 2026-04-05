"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useMemo, useState, type ReactNode } from "react";

import {
  NavRailCollapsiblePanel,
  NAV_RAIL_DESTINATION_ROW_CLASS,
  NAV_RAIL_DESTINATION_ROW_CORE,
} from "@/components/nav-rail-collapsible-panel";
import { PanelExpandButton } from "@/components/panel-expand-button";
import type { ControlSurfaceState } from "@/lib/control-surface-api";
import { finalizeServiceNavRows, type ServiceNavRow } from "@/lib/services-nav-merge";
import { useDashboardPanelOpen } from "@/lib/use-dashboard-panel-open";
import {
  isKioskPreNavigateKey,
  runKioskBeforeNavigate,
  webNavigatePathFromPlayResult,
} from "@/lib/ui-api";

/** Matches `NavDestinationGroup` subsection chrome (caption + ▴/▸ toggle). */
function PlacesNavSection({
  panelKey,
  title,
  children,
}: {
  panelKey: string;
  title: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useDashboardPanelOpen(panelKey, true);

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
      {open ? <div className="min-w-0 space-y-0.5">{children}</div> : null}
    </div>
  );
}

export function PlacesNavPanel({
  nav,
  onReload,
}: {
  nav: ControlSurfaceState["nav"];
  onReload: () => void;
}) {
  const router = useRouter();
  const [navErr, setNavErr] = useState<string | null>(null);

  const kioskRows = useMemo(
    () => finalizeServiceNavRows(nav.kiosks as unknown as ServiceNavRow[]),
    [nav.kiosks],
  );

  const onKioskClick = useCallback(
    async (e: React.MouseEvent, row: ServiceNavRow) => {
      if (!row.preNavigate || !isKioskPreNavigateKey(row.preNavigate)) return;
      e.preventDefault();
      setNavErr(null);
      try {
        const res = await runKioskBeforeNavigate(row.preNavigate);
        router.push(webNavigatePathFromPlayResult(res));
        onReload();
      } catch (x) {
        setNavErr(x instanceof Error ? x.message : "Navigation failed");
      }
    },
    [onReload, router],
  );

  const shops = nav.shops ?? [];
  const properties = nav.properties ?? [];
  const resources = nav.resources ?? [];

  return (
    <NavRailCollapsiblePanel panelKey="places-nav" title="Services & places">
      {navErr ? <p className="mb-1 text-red-400">{navErr}</p> : null}
      <div className="space-y-1.5">
        {kioskRows.length > 0 ? (
          <PlacesNavSection panelKey="places-nav-section-kiosks" title="Services">
            {kioskRows.map((k) =>
              k.preNavigate && isKioskPreNavigateKey(k.preNavigate) ? (
                <Link
                  key={`${k.key}-${k.href}`}
                  href={k.href}
                  className={NAV_RAIL_DESTINATION_ROW_CLASS}
                  onClick={(e) => void onKioskClick(e, k)}
                >
                  {k.label}
                </Link>
              ) : (
                <Link key={`${k.key}-${k.href}`} href={k.href} className={NAV_RAIL_DESTINATION_ROW_CLASS}>
                  {k.label}
                </Link>
              ),
            )}
          </PlacesNavSection>
        ) : null}
        {shops.length > 0 ? (
          <PlacesNavSection panelKey="places-nav-section-shops" title="Shipyards & vendors">
            {shops.map((s) => (
              <Link
                key={s.roomKey}
                href={`/shop?room=${encodeURIComponent(s.roomKey)}`}
                className={NAV_RAIL_DESTINATION_ROW_CLASS}
              >
                {s.label}
              </Link>
            ))}
          </PlacesNavSection>
        ) : null}
        {properties.length > 0 ? (
          <PlacesNavSection panelKey="places-nav-section-properties" title="Properties">
            {properties.map((p) => (
              <Link key={p.href} href={p.href} className={NAV_RAIL_DESTINATION_ROW_CLASS}>
                {p.label}
              </Link>
            ))}
          </PlacesNavSection>
        ) : null}
        {resources.length > 0 ? (
          <PlacesNavSection panelKey="places-nav-section-resources" title="Production sites">
            {resources.map((m) => (
              <div key={m.href} className="flex min-w-0 items-center gap-1">
                <Link href={m.href} className={`min-w-0 flex-1 ${NAV_RAIL_DESTINATION_ROW_CORE}`}>
                  {m.label}
                </Link>
                {m.active ? (
                  <span className="shrink-0 text-ui-caption text-emerald-500/90">active</span>
                ) : (
                  <span className="shrink-0 text-ui-caption text-ui-muted">idle</span>
                )}
              </div>
            ))}
          </PlacesNavSection>
        ) : null}
      </div>
    </NavRailCollapsiblePanel>
  );
}
