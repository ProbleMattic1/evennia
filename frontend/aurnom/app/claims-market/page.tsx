"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { CsPage } from "@/components/cs-page-primitives";

export default function ClaimsMarketLegacyPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/real-estate#claims-market");
  }, [router]);
  return (
    <CsPage>
      <p className="p-2 text-sm text-zinc-500 dark:text-cyan-500/80">Redirecting to Real Estate…</p>
    </CsPage>
  );
}
