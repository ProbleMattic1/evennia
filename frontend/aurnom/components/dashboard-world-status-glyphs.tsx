import type { ReactNode } from "react";

function Frame({ children }: { children: ReactNode }) {
  return (
    <svg className="size-4 shrink-0" viewBox="0 0 16 16" aria-hidden fill="none">
      {children}
    </svg>
  );
}

function norm(s: unknown): string {
  return typeof s === "string" ? s.trim().toLowerCase() : "";
}

/** Matches ``world.world_clock.compute_clock_snapshot`` day_phase values. */
export function glyphDayPhase(raw: unknown): ReactNode | null {
  switch (norm(raw)) {
    case "dawn":
      return (
        <Frame>
          <path
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            d="M2 12h12M8 4v2M4.5 6.5l1.4 1.4M11.5 6.5l-1.4 1.4"
          />
          <path
            stroke="currentColor"
            strokeWidth="1.2"
            d="M11 12a3 3 0 0 0-6 0"
          />
        </Frame>
      );
    case "day":
      return (
        <Frame>
          <circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.2" />
          <path
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            d="M8 2v1.5M8 12.5V14M2 8h1.5M12.5 8H14M3.8 3.8l1 1M11.2 11.2l1 1M12.2 3.8l-1 1M4.8 11.2l-1 1"
          />
        </Frame>
      );
    case "dusk":
      return (
        <Frame>
          <path stroke="currentColor" strokeWidth="1.2" d="M2 11h12" />
          <path
            stroke="currentColor"
            strokeWidth="1.2"
            d="M12 11a4 4 0 0 0-8 0"
          />
          <path
            stroke="currentColor"
            strokeWidth="1"
            strokeLinecap="round"
            d="M4 6l1 1M8 5v2M12 6l-1 1"
          />
        </Frame>
      );
    case "night":
      return (
        <Frame>
          <path
            fill="currentColor"
            fillOpacity={0.35}
            stroke="currentColor"
            strokeWidth="1.2"
            d="M10.5 3.5a4.5 4.5 0 1 0 4.2 6.1 3.5 3.5 0 1 1-4.2-6.1z"
          />
        </Frame>
      );
    default:
      return null;
  }
}

/** Matches ``world.world_clock`` season labels. */
export function glyphSeason(raw: unknown): ReactNode | null {
  switch (norm(raw)) {
    case "winter":
      return (
        <Frame>
          <path
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            d="M8 2v12M2 8h12M3.5 3.5l9 9M12.5 3.5l-9 9"
          />
        </Frame>
      );
    case "spring":
      return (
        <Frame>
          <path
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M8 13V7M8 7s-1.5-2-3.5-2c0 2 1.5 3.5 3.5 3.5M8 7s1.5-2 3.5-2c0-2-1.5-3.5-3.5-3.5"
          />
        </Frame>
      );
    case "summer":
      return (
        <Frame>
          <circle cx="8" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.2" />
          <path
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            d="M8 1.5v1.2M8 13.3v1.2M1.5 8h1.2M13.3 8h1.2M3.2 3.2l.9.9M11.9 11.9l.9.9M12.8 3.2l-.9.9M4.1 11.9l-.9.9"
          />
        </Frame>
      );
    case "autumn":
      return (
        <Frame>
          <path
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M8 3c-2 2.5-3 4.5-3 6.5a3 3 0 0 0 6 0c0-2-1-4-3-6.5z"
          />
          <path stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" d="M8 9.5V13" />
        </Frame>
      );
    default:
      return null;
  }
}

/** Matches ``game/world/data/world_environment.json`` default_states ids. */
export function glyphWeather(raw: unknown): ReactNode | null {
  switch (norm(raw)) {
    case "clear":
      return (
        <Frame>
          <circle cx="8" cy="7" r="2.8" stroke="currentColor" strokeWidth="1.2" />
          <path
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            d="M8 2.5v1M4.5 4.5l.9.9M2.5 8h1M13.5 8h1M11.5 4.5l-.9.9"
          />
        </Frame>
      );
    case "dust":
      return (
        <Frame>
          <path
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            d="M2 6h5M4 9h7M3 12h8"
          />
        </Frame>
      );
    case "solar_flare_watch":
      return (
        <Frame>
          <circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.2" />
          <path
            stroke="currentColor"
            strokeWidth="1"
            strokeLinecap="round"
            d="M8 1v1.8M8 13.2V15M1 8h1.8M13.2 8H15M2.6 2.6l1.3 1.3M12.1 12.1l1.3 1.3M13.4 2.6l-1.3 1.3M3.9 12.1l-1.3 1.3"
          />
        </Frame>
      );
    case "fuel_ice_fog":
      return (
        <Frame>
          <path
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            d="M3 10c1.2-1.5 2.8-2.5 5-2.5s3.8 1 5 2.5"
          />
          <circle cx="5" cy="6" r="0.9" fill="currentColor" fillOpacity={0.5} />
          <circle cx="8" cy="4.5" r="0.7" fill="currentColor" fillOpacity={0.45} />
          <circle cx="11" cy="6.5" r="0.8" fill="currentColor" fillOpacity={0.5} />
        </Frame>
      );
    default:
      return null;
  }
}

/** Matches ``typeclasses.world_environment_engine`` anomaly pool. */
export function glyphAnomaly(raw: unknown): ReactNode | null {
  switch (norm(raw)) {
    case "none":
      return null;
    case "gravity_ripple":
      return (
        <Frame>
          <path
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            d="M3 8c2-1 3-1 5 0s3 1 5 0M2.5 10.5c2.5-1.2 4.5-1.2 7 0M4 5.5c1.5-.8 2.5-.8 4 0s2.5.8 4 0"
          />
        </Frame>
      );
    case "comm_static":
      return (
        <Frame>
          <path
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4 10V6l2 2 2-4 2 4 2-2v4"
          />
        </Frame>
      );
    case "bio_spore":
      return (
        <Frame>
          <circle cx="6" cy="6" r="1.1" fill="currentColor" fillOpacity={0.55} />
          <circle cx="10" cy="7" r="1.3" fill="currentColor" fillOpacity={0.5} />
          <circle cx="7.5" cy="10.5" r="0.9" fill="currentColor" fillOpacity={0.45} />
        </Frame>
      );
    default:
      return null;
  }
}
