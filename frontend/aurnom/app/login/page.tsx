"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { UI_PREFIX } from "@/lib/ui-endpoints";

function LoginForm() {
  const searchParams = useSearchParams();
  const nextUrl = searchParams.get("next") || "/";
  const [csrfToken, setCsrfToken] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${UI_PREFIX}/auth/csrf`, { credentials: "include", cache: "no-store" });
        const data = (await res.json()) as { csrfToken?: string };
        if (!cancelled && data.csrfToken) setCsrfToken(data.csrfToken);
      } catch {
        if (!cancelled) setError("Could not load CSRF token.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const onSubmit = useCallback(() => {
    setError(null);
  }, []);

  return (
    <div className="dark mx-auto flex min-h-svh max-w-md flex-col justify-start gap-4 bg-zinc-950 p-6 pt-8 font-mono text-sm text-zinc-200">
      <h1 className="text-lg font-semibold text-cyan-300">Sign in</h1>
      <p className="text-zinc-400">Use your Aurnom account. You will be redirected after Django accepts the session.</p>
      {error && <p className="text-red-400">{error}</p>}
      <form action="/auth/login/" method="post" onSubmit={onSubmit} className="flex flex-col gap-3">
        <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
        <input type="hidden" name="next" value={nextUrl} />
        <label className="flex flex-col gap-1">
          <span className="text-zinc-500">Username</span>
          <input
            name="username"
            autoComplete="username"
            required
            className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-zinc-100"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-zinc-500">Password</span>
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-zinc-100"
          />
        </label>
        <button
          type="submit"
          disabled={!csrfToken}
          className="rounded bg-cyan-800 px-3 py-2 font-semibold text-white hover:bg-cyan-700 disabled:opacity-50"
        >
          Sign in
        </button>
      </form>
      <Link
        href="/auth/register"
        className="block w-full rounded border border-cyan-700 bg-zinc-900 px-3 py-2 text-center font-semibold text-cyan-300 hover:border-cyan-500 hover:bg-zinc-800"
      >
        Register
      </Link>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="dark flex min-h-svh items-start justify-center bg-zinc-950 px-6 pt-8 font-mono text-zinc-400">
          Loading…
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
