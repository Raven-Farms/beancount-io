import {
  graphQLErrorCodes,
  shouldClearLedgerSelection,
} from "../graphql-error-codes";

describe("graphQLErrorCodes", () => {
  it("collects every string code an Apollo error carries", () => {
    expect(
      graphQLErrorCodes({
        graphQLErrors: [
          { extensions: { code: "CONFLICT" } },
          { extensions: {} },
          { extensions: { code: 409 } },
          { extensions: { code: "FORBIDDEN" } },
        ],
      }),
    ).toEqual(["CONFLICT", "FORBIDDEN"]);
  });

  it("is empty for anything that isn't a GraphQL error", () => {
    expect(graphQLErrorCodes(new Error("Network request failed"))).toEqual([]);
    expect(graphQLErrorCodes({ graphQLErrors: "nope" })).toEqual([]);
    expect(graphQLErrorCodes(null)).toEqual([]);
    expect(graphQLErrorCodes("CONFLICT")).toEqual([]);
  });
});

// w21/182: any non-transport error at launch cleared the selected ledger, so a
// brief ledger-service outage lost it for good.
describe("shouldClearLedgerSelection", () => {
  const failure = (code?: string) => ({
    graphQLErrors: code ? [{ extensions: { code } }] : [],
    networkError: code ? null : new Error("Network request failed"),
  });

  it("clears only for a ledger that is gone or no longer accessible", () => {
    expect(shouldClearLedgerSelection(failure("NOT_FOUND"))).toBe(true);
    expect(shouldClearLedgerSelection(failure("FORBIDDEN"))).toBe(true);
  });

  it("keeps it through an outage, a rate limit or a server error", () => {
    for (const code of [
      "SERVICE_UNAVAILABLE",
      "RATE_LIMITED",
      "INTERNAL_SERVER_ERROR",
      "UNAUTHENTICATED",
    ]) {
      expect(shouldClearLedgerSelection(failure(code))).toBe(false);
    }
    expect(shouldClearLedgerSelection(failure())).toBe(false);
    expect(shouldClearLedgerSelection(new Error("timeout"))).toBe(false);
  });

  it("is what the splash decides by", () => {
    const splash = require("fs").readFileSync(
      require("path").join(
        __dirname,
        "..",
        "providers",
        "splash-provider",
        "splash-provider.tsx",
      ),
      "utf8",
    );
    expect(splash.includes("if (shouldClearLedgerSelection(err)) {")).toBe(
      true,
    );
  });
});
