import {
  classifyCreateLedgerError,
  createRequestFingerprint,
  generateDefaultLedgerName,
  isNewCreateRequest,
  isRequestIdReuse,
  ledgerSlugPreview,
  slugifyLedgerName,
} from "../ledger-name";

describe("slugifyLedgerName", () => {
  it("lowercases, replaces spaces, and strips invalid characters", () => {
    expect(slugifyLedgerName("My Book!")).toBe("my-book");
    expect(slugifyLedgerName("  Hello__World  ")).toBe("hello__world");
    expect(slugifyLedgerName("---")).toBe("");
  });
});

describe("ledgerSlugPreview", () => {
  it("previews a name the slugifier changes", () => {
    expect(ledgerSlugPreview("My Book!")).toBe("my-book");
  });

  it("shows nothing when the name needs no change", () => {
    expect(ledgerSlugPreview("my-book")).toBe(null);
    expect(ledgerSlugPreview("")).toBe(null);
  });

  it("shows nothing when the name slugifies away, instead of a dangling hint", () => {
    expect(ledgerSlugPreview("!!!")).toBe(null);
    expect(ledgerSlugPreview("---")).toBe(null);
    expect(ledgerSlugPreview("@@@")).toBe(null);
  });
});

describe("generateDefaultLedgerName", () => {
  it("starts at my-book and increments past collisions", () => {
    expect(generateDefaultLedgerName([])).toBe("my-book");
    expect(generateDefaultLedgerName(["my-book"])).toBe("my-book-1");
    expect(generateDefaultLedgerName(["my-book", "my-book-1"])).toBe(
      "my-book-2",
    );
  });
});

describe("classifyCreateLedgerError", () => {
  it("maps name conflicts and tier limits", () => {
    expect(
      classifyCreateLedgerError(
        new Error("A ledger with the name 'x' already exists."),
      ),
    ).toBe("conflict");
    expect(
      classifyCreateLedgerError({
        graphQLErrors: [{ extensions: { code: "RESOURCE_LIMIT_REACHED" } }],
      }),
    ).toBe("tier");
    expect(classifyCreateLedgerError(new Error("network down"))).toBe("other");
  });
});

describe("Sample-only template payload", () => {
  it("omits template for Starter and sends SAMPLE for Sample", () => {
    const buildVariables = (template: "STARTER" | "SAMPLE") => ({
      name: "my-book",
      private: true,
      ...(template === "SAMPLE" ? { template: "SAMPLE" } : {}),
    });
    expect(buildVariables("STARTER")).toEqual({
      name: "my-book",
      private: true,
    });
    expect(buildVariables("SAMPLE")).toEqual({
      name: "my-book",
      private: true,
      template: "SAMPLE",
    });
  });
});

// w21/434: a resumed draft lost its amount, so its next create was a different
// request under the old id, and the server refused it for a day.
describe("a create request's id", () => {
  const request = (amount: string) => ({
    name: "household",
    private: true,
    setup: { accounts: [{ name: "Assets:Bank", amount }] },
  });

  it("is told apart by what the request sends", () => {
    const first = createRequestFingerprint(request("1250.00"));
    expect(createRequestFingerprint(request("1250.00"))).toBe(first);
    expect(createRequestFingerprint(request("1300.00"))).not.toBe(first);
    expect(createRequestFingerprint(request("1250.00").setup)).not.toBe(first);
  });

  it("is kept for the same request and replaced for a changed one", () => {
    const sent = createRequestFingerprint(request("1250.00"));
    // Nothing sent yet: the id is the first request's.
    expect(isNewCreateRequest(undefined, sent)).toBe(false);
    // A retry of the same request stays idempotent.
    expect(isNewCreateRequest(sent, sent)).toBe(false);
    // A resumed draft with a retyped amount is a request of its own.
    expect(
      isNewCreateRequest(sent, createRequestFingerprint(request("99.00"))),
    ).toBe(true);
  });

  it("recognises the server's refusal of a reused id", () => {
    const refusal =
      "requestId was already used with a different creation request";
    expect(isRequestIdReuse(new Error(refusal))).toBe(true);
    expect(isRequestIdReuse({ graphQLErrors: [{ message: refusal }] })).toBe(
      true,
    );
    expect(isRequestIdReuse(new Error("Name conflict"))).toBe(false);
    expect(isRequestIdReuse(null)).toBe(false);
  });

  it("is minted again by the screen when the request changes", () => {
    const source = require("fs")
      .readFileSync(
        require("path").join(__dirname, "..", "create-ledger-screen.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "") as string;
    expect(
      source.includes(
        "if(isNewCreateRequest(sentFingerprintRef.current,fingerprint)){requestIdRef.current=newRequestId();",
      ),
    ).toBe(true);
    expect(source.includes("if(isRequestIdReuse(error)){")).toBe(true);
  });
});
