// w21/053: the Create Ledger draft kept the opening balance in plain storage
// forever, survived sign-out, and resumed days later with its old Books begin.
const removed: string[] = [];
// The module may already be loaded by another suite in this worker, so the
// loaded instance is patched rather than replaced.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const asyncStorage = require("@react-native-async-storage/async-storage");
(asyncStorage.default ?? asyncStorage).removeItem = async (key: string) => {
  removed.push(key);
};

// eslint-disable-next-line @typescript-eslint/no-require-imports
const draftModule =
  require("../create-ledger-draft") as typeof import("../create-ledger-draft");
const {
  CREATE_LEDGER_DRAFT_KEY,
  clearCreateLedgerDraft,
  restoreCreateLedgerDraft,
  serializeCreateLedgerDraft,
} = draftModule;
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { isNewCreateRequest } =
  require("../../screens/create-ledger-screen/ledger-name") as typeof import("../../screens/create-ledger-screen/ledger-name");

type Values = {
  name: string;
  currency: string;
  historyStart: string;
  openingAccount: string;
  openingAmount: string;
};

const draft = {
  step: 1,
  startKind: "preset",
  presetId: "PERSONAL",
  requestId: "req-1",
  values: {
    name: "Household",
    currency: "EUR",
    historyStart: "2026-10-20",
    openingAccount: "Assets:Bank:Checking",
    openingAmount: "1234.56",
  },
};

describe("the Create Ledger draft", () => {
  const saved = new Date(2026, 9, 20, 18, 0);

  it("is stored without the opening amount", () => {
    const raw = serializeCreateLedgerDraft(draft, saved);
    expect(raw.includes("1234.56")).toBe(false);
    expect(JSON.parse(raw).values.openingAmount).toBe("");
    // The account choice and the idempotency key resume.
    expect(JSON.parse(raw).values.openingAccount).toBe("Assets:Bank:Checking");
    expect(JSON.parse(raw).requestId).toBe("req-1");
  });

  // w21/501: a 32-bit hash of the request, amount included, let anyone reading
  // storage recover the opening balance by brute force.
  it("does not store a fingerprint that covered an opening amount", () => {
    const raw = serializeCreateLedgerDraft(
      { ...draft, sentFingerprint: "1in7xp8" },
      saved,
    );
    expect(raw.includes("1in7xp8")).toBe(false);
    expect(JSON.parse(raw).sentFingerprint).toBe("amount-not-kept");
    // It matches no request, so the resumed draft's next create is new.
    expect(isNewCreateRequest("amount-not-kept", "1in7xp8")).toBe(true);
  });

  it("keeps the fingerprint of a request that had no opening account", () => {
    const raw = serializeCreateLedgerDraft(
      {
        ...draft,
        sentFingerprint: "abc12",
        values: { ...draft.values, openingAccount: "" },
      },
      saved,
    );
    expect(JSON.parse(raw).sentFingerprint).toBe("abc12");
  });

  // w21/434: the id's request travels with it, without the amount.
  it("keeps the fingerprint of the request last sent", () => {
    const raw = serializeCreateLedgerDraft(
      {
        ...draft,
        sentFingerprint: "abc12",
        values: { ...draft.values, openingAccount: "" },
      },
      saved,
    );
    expect(JSON.parse(raw).sentFingerprint).toBe("abc12");
    expect(
      restoreCreateLedgerDraft<Values>(raw, new Date(2026, 9, 20, 21, 0))
        ?.sentFingerprint,
    ).toBe("abc12");
  });

  // w21/435: Review without the amount builds the ledger without the balance.
  it("reopens on the form when an opening account lost its amount", () => {
    const onReview = { ...draft, step: 2 };
    const restored = restoreCreateLedgerDraft<Values>(
      serializeCreateLedgerDraft(onReview, saved),
      new Date(2026, 9, 20, 21, 0),
    );
    expect(restored?.step).toBe(1);
    expect(restored?.values.openingAccount).toBe("Assets:Bank:Checking");
    expect(restored?.values.openingAmount).toBe("");
  });

  // w21/510: the amount is optional; a blank one was never lost.
  it("keeps Review for an opening account whose amount was left blank", () => {
    const blank = {
      ...draft,
      step: 2,
      values: { ...draft.values, openingAmount: "  " },
    };
    const raw = serializeCreateLedgerDraft(blank, saved);
    expect(JSON.parse(raw).amountTyped).toBe(false);
    const restored = restoreCreateLedgerDraft<Values>(
      raw,
      new Date(2026, 9, 20, 21, 0),
    );
    expect(restored?.step).toBe(2);
    expect(restored?.amountLost).toBe(false);
  });

  it("flags the lost amount of a typed draft, and of one saved before the flag", () => {
    const now = new Date(2026, 9, 20, 21, 0);
    const typed = restoreCreateLedgerDraft<Values>(
      serializeCreateLedgerDraft({ ...draft, step: 2 }, saved),
      now,
    );
    expect(typed?.amountLost).toBe(true);
    const { amountTyped: _flag, ...old } = JSON.parse(
      serializeCreateLedgerDraft({ ...draft, step: 2 }, saved),
    );
    const legacy = restoreCreateLedgerDraft<Values>(JSON.stringify(old), now);
    expect(legacy?.amountLost).toBe(true);
    expect(legacy?.step).toBe(1);
  });

  it("keeps Review for a draft with no opening account", () => {
    const onReview = {
      ...draft,
      step: 2,
      values: { ...draft.values, openingAccount: "", openingAmount: "" },
    };
    expect(
      restoreCreateLedgerDraft<Values>(
        serializeCreateLedgerDraft(onReview, saved),
        new Date(2026, 9, 20, 21, 0),
      )?.step,
    ).toBe(2);
  });

  it("resumes the same day as it was left", () => {
    const restored = restoreCreateLedgerDraft<Values>(
      serializeCreateLedgerDraft(draft, saved),
      new Date(2026, 9, 20, 21, 0),
    );
    expect(restored?.step).toBe(1);
    expect(restored?.requestId).toBe("req-1");
    expect(restored?.values.historyStart).toBe("2026-10-20");
    expect(restored?.values.openingAmount).toBe("");
  });

  it("reopens a draft from yesterday with today's Books begin", () => {
    const restored = restoreCreateLedgerDraft<Values>(
      serializeCreateLedgerDraft(draft, saved),
      new Date(2026, 9, 21, 9, 0),
    );
    expect(restored?.values.historyStart).toBe("2026-10-21");
    expect(restored?.values.currency).toBe("EUR");
  });

  it("expires with its requestId after 24 hours, and ignores old or corrupt drafts", () => {
    const raw = serializeCreateLedgerDraft(draft, saved);
    expect(restoreCreateLedgerDraft(raw, new Date(2026, 9, 21, 18, 1))).toBe(
      null,
    );
    // A draft written before this change carries no savedAt.
    expect(restoreCreateLedgerDraft(JSON.stringify(draft), saved)).toBe(null);
    expect(restoreCreateLedgerDraft("{not json", saved)).toBe(null);
    expect(restoreCreateLedgerDraft(null, saved)).toBe(null);
  });

  it("is removed by clearCreateLedgerDraft, which sign-out runs", async () => {
    await clearCreateLedgerDraft();
    expect(removed).toEqual([CREATE_LEDGER_DRAFT_KEY]);
    const signOut = require("fs").readFileSync(
      require("path").join(__dirname, "..", "server-url-actions.ts"),
      "utf8",
    ) as string;
    expect(signOut.includes("clearCreateLedgerDraft(),")).toBe(true);
  });
});

// w21/066: every keystroke saved a new savedAt, so a draft touched daily kept
// a requestId older than the server's 24-hour window.
describe("the Create Ledger draft's lifetime", () => {
  it("runs from when its requestId was minted, not from the last save", () => {
    const minted = new Date(2026, 9, 20, 9, 0).getTime();
    const raw = serializeCreateLedgerDraft(
      { ...draft, requestedAt: minted },
      new Date(2026, 9, 21, 8, 0),
    );
    expect(JSON.parse(raw).requestedAt).toBe(minted);
    expect(
      restoreCreateLedgerDraft<Values>(raw, new Date(2026, 9, 21, 8, 30))
        ?.requestId,
    ).toBe("req-1");
    expect(restoreCreateLedgerDraft(raw, new Date(2026, 9, 21, 9, 1))).toBe(
      null,
    );
  });

  it("is passed through every save of the screen", () => {
    const source = require("fs").readFileSync(
      require("path").join(
        __dirname,
        "..",
        "..",
        "screens",
        "create-ledger-screen",
        "create-ledger-screen.tsx",
      ),
      "utf8",
    ) as string;
    expect(source.includes("requestedAt: requestedAtRef.current,")).toBe(true);
    expect(source.includes("requestedAtRef.current = draft.requestedAt;")).toBe(
      true,
    );
  });
});
