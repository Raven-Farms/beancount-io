import fs from "fs";
import path from "path";
import { createRevisionCheck, isEntryGone } from "../select-entry-gone";

// A transaction removed elsewhere still opened from the list's cached copy,
// with Share and Copy link live and "Error: Ledger resource not found" buried
// in the Entry Context card (w21/013).
const graphQLError = (code: string) =>
  Object.assign(new Error("Ledger resource not found"), {
    graphQLErrors: [
      { message: "Ledger resource not found", extensions: { code } },
    ],
  });

describe("isEntryGone", () => {
  it("treats a NOT_FOUND entry context as an entry that no longer exists", () => {
    expect(isEntryGone(graphQLError("NOT_FOUND"))).toBe(true);
  });

  it("keeps a network or server failure a retryable error", () => {
    expect(isEntryGone(new Error("Network request failed"))).toBe(false);
    expect(isEntryGone(graphQLError("SERVICE_UNAVAILABLE"))).toBe(false);
    expect(isEntryGone(graphQLError("INTERNAL_SERVER_ERROR"))).toBe(false);
    expect(isEntryGone(undefined)).toBe(false);
  });
});

describe("Transaction detail for a removed entry", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "..", "transaction-detail-screen.tsx"),
    "utf8",
  );

  it("replaces the body, clearing the link actions, and refreshes the lists", () => {
    expect(source.includes("const entryGone = isEntryGone(error);")).toBe(true);
    expect(
      source.includes(
        'if (entryGone) void invalidateLedgerData(client, "entries");',
      ),
    ).toBe(true);
    // RouteLedgerUnavailable clears headerRight (route-ledger-unavailable.test).
    expect(source.includes('message={t("transactionDetailRemoved")}')).toBe(
      true,
    );
    // Decided before the cached entry renders.
    expect(
      source.indexOf("if (entryGone) {") < source.indexOf("if (!entry) {"),
    ).toBe(true);
  });
});

// w21/094: a detail lower in the stack kept showing an entry deleted above it.
describe("rechecking a detail screen on return", () => {
  it("rechecks only after the ledger was written, and once per write", () => {
    let revision = 3;
    const changed = createRevisionCheck(() => revision);
    // First focus right after the load: no extra request.
    expect(changed()).toBe(false);
    revision += 1; // a delete on the screen above
    expect(changed()).toBe(true);
    expect(changed()).toBe(false);
  });

  it("is what the detail screen refetches its entry context by", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "..", "transaction-detail-screen.tsx"),
      "utf8",
    );
    expect(
      source.includes("createRevisionCheck(() => ledgerRevisionVar())"),
    ).toBe(true);
    expect(source.includes("if (ledgerChangedSinceCheck()) {")).toBe(true);
    expect(
      source.includes("void refetchContext().catch(() => undefined);"),
    ).toBe(true);
  });
});
