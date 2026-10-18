import { useCallback, useMemo, useState } from "react";
import { useQuery } from "@apollo/client/react";
import { format, isValid } from "date-fns";
import {
  GetLedgerAccountDirectivesDocument,
  LedgerEntryType,
  type AddEntryInput,
} from "@/graphql/definitions";
import { useOpenAccountSchema } from "@/common/hooks/use-open-account-schema";

type Availability =
  | { kind: "open" }
  | { kind: "unknown"; canOpen: boolean }
  | { kind: "closed"; closedAt: string }
  | { kind: "notYetOpen"; openedAt: string };

/** The ledger date an entry is written on, or `null` while the date is invalid. */
export function entryDay(date: Date | undefined): string | null {
  return date && isValid(date) ? format(date, "yyyy-MM-dd") : null;
}

/**
 * Whether a New Entry form may name each account on the entry's date.
 * Beancount refuses an account that was never opened, one opened after the
 * entry, and one closed before it (an entry on the close date is allowed). A
 * never-opened account with a valid name can be opened in the same batch.
 */
export function useAccountAvailability(ledgerId: string) {
  const { data } = useQuery(GetLedgerAccountDirectivesDocument, {
    variables: { ledgerId },
    skip: !ledgerId,
    fetchPolicy: "cache-and-network",
  });
  // Whether a name could be opened is exactly the Open Account form's rule.
  const { schema } = useOpenAccountSchema(ledgerId);
  const [alsoOpen, setAlsoOpen] = useState<ReadonlySet<string>>(new Set());

  const directory = useMemo(
    () =>
      data &&
      new Map(
        data.getLedgerAccountDirectives.map((item) => [item.account, item]),
      ),
    [data],
  );

  const availability = useCallback(
    (account: string, day: string | null): Availability => {
      const name = account.trim();
      // Until the directory loads, leave the decision to the ledger.
      if (!directory || !name || !day) return { kind: "open" };
      const known = directory.get(name);
      if (!known) {
        return {
          kind: "unknown",
          canOpen: schema.shape.account.safeParse(name).success,
        };
      }
      if (known.openedAt > day) {
        return { kind: "notYetOpen", openedAt: known.openedAt };
      }
      if (known.closedAt && known.closedAt < day) {
        return { kind: "closed", closedAt: known.closedAt };
      }
      return { kind: "open" };
    },
    [directory, schema],
  );

  const willOpen = (account: string, day: string | null) => {
    const status = availability(account, day);
    return (
      status.kind === "unknown" &&
      status.canOpen &&
      alsoOpen.has(account.trim())
    );
  };

  return {
    availability,
    willOpen,
    setAlsoOpen: (account: string, open: boolean) =>
      setAlsoOpen((current) => {
        const next = new Set(current);
        if (open) next.add(account.trim());
        else next.delete(account.trim());
        return next;
      }),
    /** True while any named account would make the ledger refuse the entry. */
    blocks: (accounts: readonly string[], day: string | null) =>
      accounts.some(
        (account) =>
          availability(account, day).kind !== "open" && !willOpen(account, day),
      ),
    /** The `open` entries the user chose to write with this entry. */
    openEntries: (
      accounts: readonly string[],
      day: string | null,
    ): AddEntryInput[] =>
      day === null
        ? []
        : [
            ...new Set(
              accounts
                .filter((account) => willOpen(account, day))
                .map((account) => account.trim()),
            ),
          ].map((account) => ({
            type: LedgerEntryType.Open,
            open: { date: day, account, currencies: [] },
          })),
    reset: () => setAlsoOpen(new Set()),
  };
}
