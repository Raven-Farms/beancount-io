import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
} from "@apollo/client";
import { ApolloProvider, useQuery } from "@apollo/client/react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GetLedgerDocument } from "@/graphql/definitions";
import {
  Kind,
  type FieldNode,
  type OperationDefinitionNode,
  type SelectionNode,
} from "graphql";

const { toast } = vi.hoisted(() => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));
vi.mock("sonner", () => ({ toast }));
vi.mock("@tanstack/react-router", () => ({ useNavigate: () => vi.fn() }));
vi.mock("@/common/hooks/use-is-authenticated", () => ({
  useIsAuthenticated: () => true,
}));
vi.mock("@/common/hooks/use-safe-return-path", () => ({
  useSafeReturnPath: () => "/ledger/open_ledger/example",
}));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({
    t: (key: string) => key,
    i18n: { language: "en" },
  }),
}));
vi.mock("@/common/lib/errors/error-message", () => ({
  useErrorMessage: () => () => "Connection problem",
}));

import { StarButton } from "../index";

/**
 * Real Apollo with the mutation acknowledgement and every later GetLedger
 * read controlled separately (w4/m41): a confirmed star must not be undone
 * by a read that fails after it.
 */
const LEDGER_ID = "open_ledger/example";
/** Every field GetLedger selects, null unless the test sets it. */
function selected(fields: readonly SelectionNode[]): Record<string, unknown> {
  return Object.fromEntries(
    fields.flatMap((node) =>
      node.kind === Kind.FIELD ? [[node.name.value, null]] : [],
    ),
  );
}
const getLedgerFields = (
  GetLedgerDocument.definitions[0] as OperationDefinitionNode
).selectionSet.selections.find(
  (node): node is FieldNode => node.kind === Kind.FIELD,
)!.selectionSet!.selections;
const ledger = (isStarred: boolean) => ({
  ...selected(getLedgerFields),
  __typename: "Ledger",
  id: LEDGER_ID,
  name: "example",
  fullName: LEDGER_ID,
  private: false,
  empty: false,
  isStarred,
  permissions: {
    __typename: "LedgerPermissions",
    admin: false,
    pull: true,
    push: false,
  },
});

type Outcome = { success: boolean; isStarred: boolean } | "transport";

function setup(startStarred: boolean, outcome: Outcome) {
  let reads = 0;
  const writes: string[] = [];
  const client = new ApolloClient({
    cache: new InMemoryCache(),
    link: new ApolloLink(
      (operation) =>
        new Observable((observer) => {
          if (operation.operationName === "GetLedger") {
            reads += 1;
            // The first read succeeds; any later read fails.
            if (reads > 1) {
              observer.error(new Error("Failed to fetch"));
              return;
            }
            observer.next({ data: { getLedger: ledger(startStarred) } });
            observer.complete();
            return;
          }
          writes.push(operation.operationName);
          if (outcome === "transport") {
            observer.error(new Error("Failed to fetch"));
            return;
          }
          const field =
            operation.operationName === "StarLedger"
              ? "starLedger"
              : "unstarLedger";
          observer.next({
            data: {
              [field]: {
                __typename: "StarLedgerResponse",
                ...outcome,
                message: outcome.success ? "ok" : "Gitea refused",
              },
            },
          });
          observer.complete();
        }),
    ),
  });
  function Overview() {
    const { data } = useQuery(GetLedgerDocument, {
      variables: { ledgerId: LEDGER_ID },
    });
    if (!data?.getLedger) return null;
    return (
      <StarButton ledgerId={LEDGER_ID} isStarred={data.getLedger.isStarred} />
    );
  }
  render(
    <ApolloProvider client={client}>
      <Overview />
    </ApolloProvider>,
  );
  return { writes, client };
}

const STAR = "page.overview.starButton.star";
const STARRED = "page.overview.starButton.starred";

describe("StarButton acknowledgement versus a later read", () => {
  beforeEach(() => {
    toast.success.mockClear();
    toast.error.mockClear();
  });
  afterEach(() => vi.restoreAllMocks());

  it.each([
    [false, STAR, STARRED, "page.overview.starButton.starSuccess"],
    [true, STARRED, STAR, "page.overview.starButton.unstarSuccess"],
  ])(
    "keeps a confirmed change (starred before: %s) and says so, whatever a later read does",
    async (startStarred, before, after, success) => {
      const { writes, client } = setup(startStarred, {
        success: true,
        isStarred: !startStarred,
      });
      const button = await screen.findByRole("button", { name: before });

      await userEvent.click(button);

      await waitFor(() => expect(toast.success).toHaveBeenCalledWith(success));
      expect(screen.getByRole("button", { name: after })).toBeEnabled();
      expect(toast.error).not.toHaveBeenCalled();
      expect(writes).toHaveLength(1);
      // The cache holds the confirmed state, so a later remount agrees.
      expect(
        client.readQuery({
          query: GetLedgerDocument,
          variables: { ledgerId: LEDGER_ID },
        })?.getLedger?.isStarred,
      ).toBe(!startStarred);
    },
  );

  it("rolls back and explains a refused star, leaving Star to retry", async () => {
    const { writes } = setup(false, { success: false, isStarred: false });
    await userEvent.click(await screen.findByRole("button", { name: STAR }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Gitea refused"),
    );
    expect(screen.getByRole("button", { name: STAR })).toBeEnabled();
    expect(writes).toEqual(["StarLedger"]);
  });

  it("rolls back a star that never reached the server", async () => {
    setup(false, "transport");
    await userEvent.click(await screen.findByRole("button", { name: STAR }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Connection problem"),
    );
    expect(screen.getByRole("button", { name: STAR })).toBeEnabled();
    expect(toast.success).not.toHaveBeenCalled();
  });
});
