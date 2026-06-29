import type { Metadata } from "next";
import { SavedRun } from "@/components/console/SavedRun";

export const metadata: Metadata = {
  title: "Saved run · Cadenza",
  description: "A saved Cadenza market-research run — the live agent graph, decision log, and cited, claim-verified brief.",
  robots: { index: false, follow: false }, // permalinks are unguessable, not for indexing
};

export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="run-page">
      <SavedRun runId={id} />
    </main>
  );
}
