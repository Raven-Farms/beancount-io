import { createContext } from "react";

export interface LedgerSearchParams {
  account: string;
  filter: string;
  time: string;
}

interface ILedgerSearchParamsContext {
  searchParams: LedgerSearchParams;
  /**
   * Change only the given filters, against the router's latest intended
   * search — never a settled snapshot, which can be one navigation behind.
   */
  setSearchParams: (patch: Partial<LedgerSearchParams>) => void;
}

const defaultSearchParams: LedgerSearchParams = {
  account: "",
  filter: "",
  time: "",
};

export const LedgerSearchParamsContext =
  createContext<ILedgerSearchParamsContext>({
    searchParams: defaultSearchParams,
    setSearchParams: () => {},
  });
