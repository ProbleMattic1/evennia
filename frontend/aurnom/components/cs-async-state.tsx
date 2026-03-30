"use client";

import type { ReactNode } from "react";

import { CsPage } from "@/components/cs-page-primitives";

type Props = {
  loading: boolean;
  error: string | null;
  loadingLabel: string;
  errorPrefix: string;
  children: ReactNode;
};

export function CsAsyncState({ loading, error, loadingLabel, errorPrefix, children }: Props) {
  if (loading) {
    return (
      <CsPage>
        <p className="text-sm text-ui-accent-readable">{loadingLabel}</p>
      </CsPage>
    );
  }
  if (error) {
    return (
      <CsPage>
        <p className="text-sm text-red-600 dark:text-red-400">
          {errorPrefix}: {error}
        </p>
      </CsPage>
    );
  }
  return <>{children}</>;
}
