/**
 * A real ApolloClient with the app's default options over a cache restored the
 * way `cache-persist.ts` restores it, so a cold start is reproduced exactly.
 * With Apollo's own `cache-first` default, a query without a policy of its own
 * (Transactions, Merchants) answered from the last session's cache and never
 * asked the network (w21/006).
 *
 * Relative requires: the jest-lite runner has no `@/` alias for value imports.
 */
import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
  gql,
} from "@apollo/client";
import { APOLLO_DEFAULT_OPTIONS } from "../default-options";

const JOURNAL = gql`
  query journal($ledgerId: String!) {
    journal(ledgerId: $ledgerId) {
      payee
    }
  }
`;

const row = (payee: string) => ({ __typename: "Row", payee });

/** Last session's cache: FARMERS MARKET is the newest row. */
const persisted = () => {
  const cache = new InMemoryCache();
  cache.writeQuery({
    query: JOURNAL,
    variables: { ledgerId: "alice/main" },
    data: { journal: [row("FARMERS MARKET")] },
  });
  const restored = new InMemoryCache();
  restored.restore(cache.extract());
  return restored;
};

function coldStart(defaultOptions = APOLLO_DEFAULT_OPTIONS) {
  const state = { calls: 0 };
  const link = new ApolloLink(
    () =>
      new Observable((observer) => {
        state.calls += 1;
        // Written since the last session, outside the app.
        observer.next({
          data: { journal: [row("qa-gym"), row("FARMERS MARKET")] },
        });
        observer.complete();
      }),
  );
  const client = new ApolloClient({ link, cache: persisted(), defaultOptions });
  return { client, state };
}

/** Every payee list a watcher delivers until the stream goes quiet. */
async function watch(client: ApolloClient<unknown>): Promise<string[][]> {
  const seen: string[][] = [];
  const subscription = client
    .watchQuery({ query: JOURNAL, variables: { ledgerId: "alice/main" } })
    .subscribe(({ data }) => {
      if (data) {
        seen.push(
          (data as { journal: { payee: string }[] }).journal.map(
            (r) => r.payee,
          ),
        );
      }
    });
  await new Promise((resolve) => setTimeout(resolve, 50));
  subscription.unsubscribe();
  return seen;
}

describe("Apollo default options", () => {
  it("renders the persisted rows, then the network's, on a cold start", async () => {
    const { client, state } = coldStart();
    const seen = await watch(client);
    expect(state.calls).toBe(1);
    expect(seen[0]).toEqual(["FARMERS MARKET"]);
    expect(seen[seen.length - 1]).toEqual(["qa-gym", "FARMERS MARKET"]);
  });

  it("is what the bug was without them: the cache answers alone", async () => {
    const { client, state } = coldStart({});
    const seen = await watch(client);
    expect(state.calls).toBe(0);
    expect(seen).toEqual([["FARMERS MARKET"]]);
  });

  it("does not go back to the network on a later cache write", async () => {
    const { client, state } = coldStart();
    const seen: number[] = [];
    const subscription = client
      .watchQuery({ query: JOURNAL, variables: { ledgerId: "alice/main" } })
      .subscribe(() => seen.push(state.calls));
    await new Promise((resolve) => setTimeout(resolve, 50));
    client.cache.writeQuery({
      query: JOURNAL,
      variables: { ledgerId: "alice/main" },
      data: { journal: [row("edited")] },
    });
    await new Promise((resolve) => setTimeout(resolve, 50));
    subscription.unsubscribe();
    expect(state.calls).toBe(1);
  });
});
