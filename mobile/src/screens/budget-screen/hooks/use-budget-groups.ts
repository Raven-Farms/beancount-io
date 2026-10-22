import { useCallback, useEffect, useMemo, useState } from "react";
import { useApolloClient } from "@apollo/client";
import {
  GetLedgerJournalDocument,
  useGetLedgerJournalQuery,
  type GetLedgerJournalQuery,
} from "@/generated-graphql/graphql";
import { useToday } from "@/common/hooks/use-today";
import { readBudgetPages } from "./read-budget-pages";
import { DirectiveType } from "@/screens/transactions-screen/types";
import {
  groupBudgetEntries,
  type BudgetEntry,
} from "@/screens/budget-screen/selectors/budget-selectors";

/**
 * Budget directives are read through the generic journal query, filtered to
 * `custom "budget"`. The server's default page size is 20 and it truncates
 * silently, so the first page asks for a size big enough to cover most budget
 * sets. The response carries `total`: when more exist, the rest are read after
 * the first page (w21/397). Until every page is in, the groups are not built,
 * and a failed later page is an error with a retry: a budget set missing its
 * oldest directives would compare against the wrong targets and drop a card.
 */
const BUDGET_DIRECTIVE_LIMIT = 500;

function budgetQuery(offset = 0) {
  return {
    offset,
    limit: BUDGET_DIRECTIVE_LIMIT,
    directiveTypes: [DirectiveType.CUSTOM],
    customSubtypes: ["budget"],
  };
}

/** Shared variables so the page and the home panel hit the same cache entry. */
function budgetJournalVariables(ledgerId: string, offset = 0) {
  return { ledgerId, query: budgetQuery(offset) };
}

type Page = { total: number; data: unknown[] };

export function useBudgetGroups(ledgerId?: string, refreshSignal = 0) {
  const client = useApolloClient();
  const { data, loading, error, refetch } = useGetLedgerJournalQuery({
    variables: budgetJournalVariables(ledgerId!),
    skip: !ledgerId,
    // The client's cache-and-network default: a budget removed outside the
    // app must not linger on Home from the persisted cache (w21/006).
  });

  useEffect(() => {
    if (refreshSignal > 0 && ledgerId) {
      void refetch().catch(() => undefined);
    }
  }, [refreshSignal, ledgerId, refetch]);

  const firstPage = data?.getLedgerJournal as Page | undefined;
  const needsMore = !!firstPage && firstPage.data.length < firstPage.total;

  // The pages after the first, read once `total` says more exist, tied to the
  // first page they follow so a refetched first page reads them again.
  const [attempt, setAttempt] = useState(0);
  const [rest, setRest] = useState<{
    after: Page;
    data: unknown[];
    error?: Error;
  } | null>(null);
  useEffect(() => {
    if (!ledgerId || !firstPage || !needsMore) return;
    let cancelled = false;
    void (async () => {
      try {
        const pages = await readBudgetPages(
          firstPage.data.length,
          firstPage.total,
          BUDGET_DIRECTIVE_LIMIT,
          async (offset) => {
            const result = await client.query<GetLedgerJournalQuery>({
              query: GetLedgerJournalDocument,
              variables: budgetJournalVariables(ledgerId, offset),
              fetchPolicy: "network-only",
            });
            return (result.data?.getLedgerJournal.data ?? []) as unknown[];
          },
        );
        if (!cancelled) setRest({ after: firstPage, data: pages });
      } catch (caught) {
        if (!cancelled) {
          setRest({ after: firstPage, data: [], error: caught as Error });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [client, ledgerId, firstPage, needsMore, attempt]);

  const restForPage = rest?.after === firstPage ? rest : null;
  const complete =
    !!firstPage && (!needsMore || (!!restForPage && !restForPage.error));
  const restError = restForPage?.error;

  // Which directive is in effect depends on the day: a change scheduled for
  // 1 November must take over on a Home or Budget screen left open across it,
  // where Apollo hands back the same `data` (w21/078).
  const today = useToday();
  const groups = useMemo(
    () =>
      groupBudgetEntries(
        (complete && firstPage
          ? [...firstPage.data, ...(restForPage?.data ?? [])]
          : []) as unknown as BudgetEntry[],
        today,
      ),
    [complete, firstPage, restForPage, today],
  );

  const reload = useCallback(
    (...args: Parameters<typeof refetch>) => {
      setAttempt((current) => current + 1);
      return refetch(...args);
    },
    [refetch],
  );

  // An empty `groups` cannot tell "no budgets" from "not loaded yet".
  return {
    groups,
    loaded: complete,
    loading: loading || (!!firstPage && !complete && !restError),
    error: error ?? restError,
    refetch: reload,
  };
}

/**
 * Outcome of a budget write. Shared by the save and delete hooks so both
 * report failure the same way and their callers can handle one shape.
 */
export type BudgetMutationResult =
  { ok: true } | { ok: false; message: string | null };
