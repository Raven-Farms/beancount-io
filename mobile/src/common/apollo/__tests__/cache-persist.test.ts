/**
 * Pins the cache-persist wiring: key, maxSize, restore-before-render gate.
 * Source asserts avoid pulling AsyncStorage / apollo3-cache-persist into the
 * runner where they need native modules.
 */
const fs = require("fs");
const path = require("path");

describe("apollo cache persist wiring", () => {
  it("declares an explicit maxSize and write trigger", () => {
    const src = fs.readFileSync(
      path.join(__dirname, "../cache-persist.ts"),
      "utf8",
    );
    expect(src.includes("APOLLO_CACHE_MAX_SIZE = 1024 * 1024")).toBe(true);
    expect(src.includes('trigger: "write"')).toBe(true);
    expect(src.includes("CachePersistor")).toBe(true);
  });

  // w21/227: past the cap the library deletes the stored cache and pauses for
  // the rest of the session; the snapshot is trimmed to fit instead.
  it("trims an oversized snapshot to the cap instead of letting it pause", () => {
    const src = fs.readFileSync(
      path.join(__dirname, "../cache-persist.ts"),
      "utf8",
    );
    expect(
      src
        .replace(/\s+/g, "")
        .includes(
          "persistenceMapper:async(snapshot:string)=>fitCacheSnapshot(snapshot,APOLLO_CACHE_MAX_SIZE)",
        ),
    ).toBe(true);
  });

  // w21/350: a write's invalidation must not save the evicted cache.
  it("holds saving while a ledger invalidation refetches", () => {
    const src = fs.readFileSync(
      path.join(__dirname, "../cache-persist.ts"),
      "utf8",
    );
    expect(
      src
        .replace(/\s+/g, "")
        .includes(
          "setInvalidationPersistence(createInvalidationGuard(cachePersistor))",
        ),
    ).toBe(true);
  });

  it("gates splash ready on restoreApolloCache", () => {
    const src = fs.readFileSync(
      path.join(
        __dirname,
        "../../providers/splash-provider/splash-provider.tsx",
      ),
      "utf8",
    );
    expect(src.includes("restoreApolloCache()")).toBe(true);
    expect(src.includes('from "@/common/apollo/cache-persist"')).toBe(true);
  });
});
