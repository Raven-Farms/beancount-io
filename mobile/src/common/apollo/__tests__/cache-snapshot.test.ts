/**
 * The persisted cache must survive one large read (w21/227). Driven through
 * the real `CachePersistor` with the app's size cap, on a Map-backed store,
 * as the reviewer reproduced it.
 *
 * Relative requires: the jest-lite runner has no `@/` alias for value imports.
 */
import { ApolloClient, InMemoryCache, gql } from "@apollo/client";
import { CachePersistor } from "apollo3-cache-persist";
import { fitCacheSnapshot } from "../cache-snapshot";

const MAX = 1024 * 1024;

class MapStorage {
  readonly data = new Map<string, string>();
  getItem(key: string) {
    return Promise.resolve(this.data.get(key) ?? null);
  }
  setItem(key: string, value: string | null) {
    if (value === null) this.data.delete(key);
    else this.data.set(key, value);
    return Promise.resolve();
  }
  removeItem(key: string) {
    this.data.delete(key);
    return Promise.resolve();
  }
}

const SMALL = gql`
  query Small {
    health
  }
`;
const FILE = gql`
  query File($path: String!) {
    getLedgerFile(path: $path) {
      content
    }
  }
`;

function harness(withMapper: boolean) {
  const cache = new InMemoryCache();
  const storage = new MapStorage();
  const persistor = new CachePersistor({
    cache,
    storage,
    key: "apollo-cache-persist",
    maxSize: MAX,
    trigger: "write",
    ...(withMapper
      ? { persistenceMapper: async (s: string) => fitCacheSnapshot(s, MAX) }
      : {}),
  });
  // Typed away: only the cache is needed.
  void ApolloClient;
  return { cache, storage, persistor };
}

describe("a snapshot over the size cap", () => {
  it("is trimmed to fit, keeping the small reads and dropping the big one", async () => {
    const { cache, storage, persistor } = harness(true);
    cache.writeQuery({ query: SMALL, data: { health: "OK" } });
    cache.writeQuery({
      query: FILE,
      variables: { path: "main.bean" },
      data: {
        getLedgerFile: {
          __typename: "LedgerFile",
          content: "x".repeat(MAX + 100_000),
        },
      },
    });
    await persistor.persist();
    const saved = storage.data.get("apollo-cache-persist") ?? "";
    expect(saved.length > 0 && saved.length <= MAX).toBe(true);
    expect(saved.includes('"health":"OK"')).toBe(true);
    expect(saved.includes("getLedgerFile")).toBe(false);
  });

  it("keeps saving afterwards, once the big read is gone", async () => {
    const { cache, storage, persistor } = harness(true);
    cache.writeQuery({
      query: FILE,
      variables: { path: "main.bean" },
      data: {
        getLedgerFile: {
          __typename: "LedgerFile",
          content: "x".repeat(MAX + 1),
        },
      },
    });
    await persistor.persist();
    cache.evict({ id: "ROOT_QUERY", fieldName: "getLedgerFile" });
    cache.writeQuery({ query: SMALL, data: { health: "OK" } });
    await persistor.persist();
    expect(
      (storage.data.get("apollo-cache-persist") ?? "").includes(
        '"health":"OK"',
      ),
    ).toBe(true);
    expect(persistor.persistor.paused).toBe(false);
  });

  it("is the bug without the mapper: stored cache deleted, saving paused", async () => {
    const { cache, storage, persistor } = harness(false);
    cache.writeQuery({ query: SMALL, data: { health: "OK" } });
    await persistor.persist();
    expect(storage.data.size).toBe(1);
    cache.writeQuery({
      query: FILE,
      variables: { path: "main.bean" },
      data: {
        getLedgerFile: {
          __typename: "LedgerFile",
          content: "x".repeat(MAX + 1),
        },
      },
    });
    await persistor.persist();
    expect(storage.data.size).toBe(0);
    expect(persistor.persistor.paused).toBe(true);
  });
});

describe("fitCacheSnapshot", () => {
  it("returns a snapshot that already fits untouched", () => {
    const small = JSON.stringify({ ROOT_QUERY: { a: 1 } });
    expect(fitCacheSnapshot(small, MAX)).toBe(small);
  });

  it("drops the largest top-level reads first", () => {
    const snapshot = JSON.stringify({
      ROOT_QUERY: {
        big: "x".repeat(600),
        medium: "y".repeat(300),
        small: "z",
      },
    });
    const fitted = JSON.parse(fitCacheSnapshot(snapshot, 500)) as {
      ROOT_QUERY: Record<string, string>;
    };
    expect(Object.keys(fitted.ROOT_QUERY).sort()).toEqual(["medium", "small"]);
  });

  it("saves nothing rather than something it cannot fit", () => {
    const snapshot = JSON.stringify({
      ROOT_QUERY: { a: 1 },
      "Entity:1": { blob: "x".repeat(2000) },
    });
    expect(fitCacheSnapshot(snapshot, 500)).toBe("{}");
    expect(fitCacheSnapshot("not json" + " ".repeat(600), 500)).toBe("{}");
  });
});
