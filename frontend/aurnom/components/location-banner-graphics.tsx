import type { ReactNode } from "react";

function SvgFrame({ children }: { children: ReactNode }) {
  return (
    <svg className="size-14 shrink-0 text-current opacity-90 md:size-16" viewBox="0 0 64 64" aria-hidden fill="none">
      {children}
    </svg>
  );
}

/** Inline silhouettes keyed by ``RoomAmbientBannerSlide.graphicKey``. */
export const BANNER_GRAPHIC_REGISTRY: Record<string, ReactNode> = {
  promenade: (
    <SvgFrame>
      <path
        fill="currentColor"
        fillOpacity={0.35}
        d="M8 52V20l10-8 12 6 12-6 10 8v32H8zm10-28v20h8V24l-8-6zm14 6v14h8V28l-8-4zm14 4v16h8V32l-8-4z"
      />
      <rect x="14" y="44" width="36" height="4" rx="1" fill="currentColor" fillOpacity={0.5} />
    </SvgFrame>
  ),
  industrial: (
    <SvgFrame>
      <path stroke="currentColor" strokeWidth="2" strokeOpacity={0.6} d="M12 52V28l8-4v8l8-6v10l8-5v16" />
      <rect x="10" y="52" width="44" height="4" fill="currentColor" fillOpacity={0.45} />
      <circle cx="48" cy="22" r="6" stroke="currentColor" strokeWidth="2" strokeOpacity={0.5} />
    </SvgFrame>
  ),
  refinery: (
    <SvgFrame>
      <path fill="currentColor" fillOpacity={0.4} d="M14 52V32l6-3v6l8-5v22H14zm16-18v18h8V30l-4-2v-4l4-2zm12 8v12h8V40l-4-6z" />
      <ellipse cx="32" cy="14" rx="10" ry="4" stroke="currentColor" strokeWidth="1.5" strokeOpacity={0.5} />
    </SvgFrame>
  ),
  asteroid: (
    <SvgFrame>
      <circle cx="32" cy="32" r="18" stroke="currentColor" strokeWidth="2" strokeOpacity={0.55} />
      <path
        fill="currentColor"
        fillOpacity={0.3}
        d="M22 28h6v8h-6zm14-6h8v10h-8zm-4 18h10v6H32z"
      />
    </SvgFrame>
  ),
  bazaar: (
    <SvgFrame>
      <path
        stroke="currentColor"
        strokeWidth="2"
        strokeOpacity={0.55}
        d="M12 40c4-8 8-12 16-12s12 4 16 12M18 52h28M20 46h24"
      />
      <circle cx="24" cy="24" r="3" fill="currentColor" fillOpacity={0.4} />
      <circle cx="40" cy="22" r="3" fill="currentColor" fillOpacity={0.35} />
    </SvgFrame>
  ),
};
