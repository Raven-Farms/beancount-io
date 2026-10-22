// w21/350: the persistor saves on every cache write, evictions included, so a
// refetch that failed after an eviction left the empty cache on disk. Relative
// requires: the jest-lite runner has no `@/` alias for value imports.
const QUERY = `query getLedgerErrors($ledgerId: String!) {
  getLedgerErrors(ledgerId: $ledgerId) { filename lineno message }
}`;

function makeClient(failRefetch: boolean) {
  const {
    ApolloClient,
    InMemoryCache,
    ApolloLink,
    Observable,
    gql,
  } = require("@apollo/client");
  let calls = 0;
  const link = new ApolloLink(
    () =>
      new Observable(
        (observer: {
          next: (v: unknown) => void;
          error: (e: Error) => void;
          complete: () => void;
        }) => {
          calls += 1;
          if (failRefetch && calls > 1) {
            observer.error(new Error("offline"));
            return;
          }
          observer.next({
            data: {
              getLedgerErrors: [
                {
                  __typename: "LedgerError",
                  filename: "main.bean",
                  lineno: calls,
                  message: "m",
                },
              ],
            },
          });
          observer.complete();
        },
      ),
  );
  const client = new ApolloClient({ link, cache: new InMemoryCache() });
  // A mounted screen: its query is watched, so the eviction refetches it.
  const watched = client.watchQuery({
    query: gql(QUERY),
    variables: { ledgerId: "L" },
  });
  watched.subscribe({ next: () => undefined, error: () => undefined });
  return client;
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 50));

function fakePersistor() {
  const log: string[] = [];
  return {
    log,
    pause: () => void log.push("pause"),
    resume: () => void log.push("resume"),
    persist: async () => void log.push("persist"),
  };
}

async function invalidateWith(failRefetch: boolean) {
  const {
    invalidateLedgerData,
    createInvalidationGuard,
    setInvalidationPersistence,
  } = require("../invalidate-ledger");
  const persistor = fakePersistor();
  setInvalidationPersistence(createInvalidationGuard(persistor));
  const client = makeClient(failRefetch);
  await settle();
  const warn = console.warn;
  console.warn = () => undefined;
  try {
    await invalidateLedgerData(client, "entries");
    await settle();
  } finally {
    console.warn = warn;
    setInvalidationPersistence(null);
  }
  return persistor.log;
}

describe("ledger invalidation and the cache persistor", () => {
  it("saves the refreshed cache once the refetch succeeded", async () => {
    expect(await invalidateWith(false)).toEqual(["pause", "resume", "persist"]);
  });

  it("keeps the disk copy when the refetch failed", async () => {
    expect(await invalidateWith(true)).toEqual(["pause", "resume"]);
  });

  it("overlapping invalidations share one pause and save only if none failed", () => {
    const { createInvalidationGuard } = require("../invalidate-ledger");
    const persistor = fakePersistor();
    const guard = createInvalidationGuard(persistor);
    guard.begin();
    guard.begin();
    guard.end(true);
    expect(persistor.log).toEqual(["pause", "pause"]);
    guard.end(false);
    expect(persistor.log).toEqual(["pause", "pause", "resume"]);
    guard.begin();
    guard.end(true);
    expect(persistor.log).toEqual([
      "pause",
      "pause",
      "resume",
      "pause",
      "resume",
      "persist",
    ]);
  });
});
