import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from "react";
import { useApolloClient } from "@apollo/client";
import { LedgerDirectory } from "./ledger-directory";

const Context = createContext<LedgerDirectory | null>(null);

export function LedgerDirectoryProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const client = useApolloClient();
  const directory = useMemo(() => new LedgerDirectory(client), [client]);
  useEffect(() => {
    // Cached rows first, then a revalidation; an error is rendered by the drawer.
    void directory.revalidate().catch(() => {});
    return directory.dispose;
  }, [directory]);
  return <Context.Provider value={directory}>{children}</Context.Provider>;
}

export function useLedgerDirectory() {
  const directory = useContext(Context);
  if (!directory) throw new Error("Ledger directory provider not found");
  const state = useSyncExternalStore(
    directory.subscribe,
    directory.getSnapshot,
  );
  return { ...state, refresh: directory.refresh };
}

/** The directory when one is provided (the signed-in app), otherwise null. */
export function useOptionalLedgerDirectory(): LedgerDirectory | null {
  return useContext(Context);
}
