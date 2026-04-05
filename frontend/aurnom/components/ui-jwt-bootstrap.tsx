"use client";

import { useEffect, useRef } from "react";

import { fetchTokensFromSession, getAccessToken, setUiTokens } from "@/lib/ui-auth-token";

/**
 * After Django session login, obtain JWT for `/api/ui/*` calls.
 * Runs once on mount when session is authenticated but no access token is stored.
 */
export function UiJwtBootstrap() {
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    (async () => {
      if (getAccessToken()) return;
      const statusRes = await fetch("/api/ui/auth/status", { credentials: "include", cache: "no-store" });
      if (!statusRes.ok) return;
      const status = (await statusRes.json()) as { authenticated?: boolean };
      if (!status.authenticated) return;
      const tokens = await fetchTokensFromSession();
      if (tokens?.ok && tokens.access && tokens.refresh) {
        setUiTokens(tokens.access, tokens.refresh);
        window.dispatchEvent(new Event("aurnom:jwt-ready"));
      }
    })();
  }, []);

  return null;
}
