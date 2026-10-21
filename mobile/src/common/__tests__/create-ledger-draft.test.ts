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
