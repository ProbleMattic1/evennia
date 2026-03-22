import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-10">
      <header className="rounded-2xl bg-zinc-950 p-8 text-white">
        <h1 className="text-3xl font-bold">Aurnom</h1>
        <p className="mt-3 max-w-2xl text-zinc-300">
          Frontend entry point for the Evennia-powered world. Start with play,
          bank, or shipyard.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <Link href="/play" className="rounded-xl border p-6 hover:bg-zinc-50">
          <h2 className="text-xl font-semibold">Play</h2>
          <p className="mt-2 text-sm text-zinc-600">
            Story output box plus button-based exits and actions.
          </p>
        </Link>

        <Link href="/bank" className="rounded-xl border p-6 hover:bg-zinc-50">
          <h2 className="text-xl font-semibold">Bank</h2>
          <p className="mt-2 text-sm text-zinc-600">
            Alpha Prime treasury and financial overview.
          </p>
        </Link>

        <Link href="/shipyard" className="rounded-xl border p-6 hover:bg-zinc-50">
          <h2 className="text-xl font-semibold">Shipyard</h2>
          <p className="mt-2 text-sm text-zinc-600">
            Real shipyard inventory from the game world.
          </p>
        </Link>
      </section>
    </main>
  );
}
