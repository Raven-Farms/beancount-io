import { createFileRoute, notFound } from "@tanstack/react-router";
import NotFoundPage from "@/common/root-route/not-found-page";

export const Route = createFileRoute("/$")({
  // Matching this catch-all means no real route owns the URL — throw so SSR
  // answers 404 the same way the ledger loader does for missing ledgers.
  loader: () => {
    throw notFound();
  },
  // The shared not-found page owns the title, including the requested path.
  component: NotFoundPage,
});
