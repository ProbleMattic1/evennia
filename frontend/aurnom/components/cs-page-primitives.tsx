"use client";

import Link from "next/link";
import type { ReactNode } from "react";

export function CsPage({ children }: { children: ReactNode }) {
  return (
    <main className="dark min-h-svh bg-zinc-950 font-mono text-[11px] text-zinc-300">{children}</main>
  );
}

export function CsHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="border-b border-cyan-900/40 px-1.5 py-1.5">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <h1 className="truncate text-[12px] font-bold uppercase tracking-widest text-cyan-400">{title}</h1>
          {subtitle ? <p className="truncate text-[10px] text-ui-muted">{subtitle}</p> : null}
        </div>
        {actions ? <div className="flex shrink-0 items-center gap-1">{actions}</div> : null}
      </div>
    </header>
  );
}

export function CsPanel({
  title,
  children,
  className = "",
}: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`mb-1 ${className}`}>
      <div className="bg-cyan-900/30 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-cyan-300">
        {title}
      </div>
      <div className="border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-[11px]">{children}</div>
    </section>
  );
}

export function CsButtonLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="rounded border border-cyan-800/60 px-1.5 py-0.5 text-[10px] text-cyan-400 hover:bg-cyan-900/40"
    >
      {children}
    </Link>
  );
}

export function CsColumns({ left, right }: { left: ReactNode; right?: ReactNode }) {
  return (
    <div className={`grid gap-1.5 p-1.5 ${right ? "lg:grid-cols-2" : "grid-cols-1"}`}>
      <div className="min-w-0">{left}</div>
      {right ? <div className="min-w-0">{right}</div> : null}
    </div>
  );
}
