import fs from "fs";
import path from "path";
import {
  ACCOUNT_ROOT_PREFIXES,
  composeAccountName,
  openAccountSubmitState,
  peelTypedRoot,
  splitPrefillAccountName,
  typedSubPathIssue,
  type AccountNameValidationReason,
  validateAccountName,
} from "../screens/open-account-screen/account-name";
import { buildOpenAccountEntry } from "../screens/open-account-screen/open-account-entry";

describe("open account name", () => {
  it("combines every dropdown prefix with the entered sub-path", () => {
    for (const prefix of ACCOUNT_ROOT_PREFIXES) {
      const account = composeAccountName(prefix, "Bank:Checking");

      expect(account).toBe(`${prefix}:Bank:Checking`);
      expect(validateAccountName(account)).toEqual({ ok: true });
    }
  });

  it("reports the precise reason for each invalid account shape", () => {
    const invalidNames: Array<[string, AccountNameValidationReason]> = [
      ["Assets", "tooFewComponents"],
      ["Unknown:Bank", "invalidRoot"],
      ["Assets::Checking", "emptyComponent"],
      ["Assets:bank", "componentMustStartUppercase"],
      ["Assets:Bank_Checking", "invalidCharacters"],
    ];

    for (const [name, reason] of invalidNames) {
      expect(validateAccountName(name)).toEqual({ ok: false, reason });
    }
  });

  it("trims the entered components and collapses stray separators", () => {
    expect(composeAccountName("Assets", " :Bank:: Checking: ")).toBe(
      "Assets:Bank:Checking",
    );
    expect(composeAccountName("Assets", "")).toBe("Assets");
  });

  it("allows digits and hyphens after a component's uppercase initial", () => {
    expect(validateAccountName("Assets:US:PreTax401k")).toEqual({ ok: true });
    expect(validateAccountName("Equity:Opening-Balances")).toEqual({
      ok: true,
    });
  });

  // Note 165: the validator applied ASCII-only rules to every component, so two
  // shapes the Beancount grammar accepts were rejected — a digit-led
  // subcomponent and a non-ASCII uppercase initial (`/^[A-Z]/` has no `u` flag).
  it("accepts a digit-led subcomponent", () => {
    for (const name of [
      "Assets:US:401k",
      "Liabilities:2026-Loan",
      "Expenses:Travel:2026",
    ]) {
      expect(validateAccountName(name)).toEqual({ ok: true });
    }
  });

  it("accepts Unicode uppercase initials and bodies in subcomponents", () => {
    for (const name of [
      "Assets:Épargne",
      "Expenses:Café",
      "Assets:Банк:Счёт",
      "Assets:Ärzte",
      // A Unicode body after an ASCII initial, too.
      "Expenses:Food:Crème",
    ]) {
      expect(validateAccountName(name)).toEqual({ ok: true });
    }
  });

  it("accepts a caseless-script initial, which the ledger grammar allows", () => {
    // Han, Hiragana, Arabic and Hebrew letters are `\p{Lo}`: they have no
    // uppercase form, so an "uppercase or digit" rule would reject them even
    // though the Beancount lexer (which keys off non-ASCII bytes, not case)
    // accepts them. A caseless letter is admitted instead.
    for (const name of [
      "Expenses:日本",
      "Expenses:日本:交通",
      "Expenses:العربية",
      "Expenses:עברית",
      "Expenses:ひらがな",
    ]) {
      expect(validateAccountName(name)).toEqual({ ok: true });
    }
    // The same characters are fine once they are not the initial, too.
    expect(validateAccountName("Expenses:Japan日本")).toEqual({ ok: true });
  });

  it("still rejects a lowercase-led name in a cased script", () => {
    // The caseless allowance must not become a loophole for scripts that do
    // distinguish case.
    for (const name of [
      "Expenses:food",
      "Expenses:épargne",
      "Expenses:ελληνικά",
      "Expenses:русский",
    ]) {
      expect(validateAccountName(name)).toEqual({
        ok: false,
        reason: "componentMustStartUppercase",
      });
    }
  });

  it("still rejects lowercase-led, underscored and spaced subcomponents", () => {
    const invalid: Array<[string, AccountNameValidationReason]> = [
      ["Assets:bank", "componentMustStartUppercase"],
      ["Assets:épargne", "componentMustStartUppercase"],
      ["Assets:Bank_Checking", "invalidCharacters"],
      ["Assets:Bank Checking", "invalidCharacters"],
      ["Assets:Café Noir", "invalidCharacters"],
      ["Assets:Bank:visa", "componentMustStartUppercase"],
    ];
    for (const [name, reason] of invalid) {
      expect(validateAccountName(name)).toEqual({ ok: false, reason });
    }
  });

  it("keeps the root strictly ASCII and canonical", () => {
    // The five roots are fixed names, so the relaxed subcomponent rules must not
    // let a Unicode or digit-led root through.
    expect(validateAccountName("Équity:Opening")).toEqual({
      ok: false,
      reason: "invalidRoot",
    });
    expect(validateAccountName("401k:Savings")).toEqual({
      ok: false,
      reason: "invalidRoot",
    });
  });
});

describe("splitPrefillAccountName", () => {
  it("splits a canonical name into its root and verbatim sub-path", () => {
    expect(splitPrefillAccountName("Expenses:Coffee")).toEqual({
      rootPrefix: "Expenses",
      subPath: "Coffee",
    });
    expect(splitPrefillAccountName("Assets:Bank:Checking")).toEqual({
      rootPrefix: "Assets",
      subPath: "Bank:Checking",
    });
  });

  it("matches the root case-insensitively but keeps the sub-path verbatim", () => {
    expect(splitPrefillAccountName("expenses:coffee")).toEqual({
      rootPrefix: "Expenses",
      subPath: "coffee",
    });
    expect(splitPrefillAccountName("LIABILITIES:Visa")).toEqual({
      rootPrefix: "Liabilities",
      subPath: "Visa",
    });
  });

  it("treats a bare root as that root with an empty sub-path", () => {
    for (const root of ACCOUNT_ROOT_PREFIXES) {
      expect(splitPrefillAccountName(root.toLowerCase())).toEqual({
        rootPrefix: root,
        subPath: "",
      });
    }
  });

  it("puts a rootless string under the fallback root, trimmed but unrewritten", () => {
    expect(splitPrefillAccountName("coffee shop", "Expenses")).toEqual({
      rootPrefix: "Expenses",
      subPath: "coffee shop",
    });
    expect(splitPrefillAccountName("  Coffee  ")).toEqual({
      rootPrefix: "Assets",
      subPath: "Coffee",
    });
  });

  it("does not mistake a root-prefixed word for a root", () => {
    expect(splitPrefillAccountName("Assetsy:Thing", "Expenses")).toEqual({
      rootPrefix: "Expenses",
      subPath: "Assetsy:Thing",
    });
  });

  it("round-trips a valid typed name through composeAccountName", () => {
    for (const name of ["Expenses:Coffee", "Assets:Bank:Checking"]) {
      const { rootPrefix, subPath } = splitPrefillAccountName(name);
      expect(composeAccountName(rootPrefix, subPath)).toBe(name);
      expect(validateAccountName(name)).toEqual({ ok: true });
    }
  });

  it("leaves an invalid sub-path for the screen's validation to reject", () => {
    const { rootPrefix, subPath } = splitPrefillAccountName(
      "coffee shop",
      "Expenses",
    );
    const composed = composeAccountName(rootPrefix, subPath);
    expect(composed).toBe("Expenses:coffee shop");
    expect(validateAccountName(composed)).toEqual({
      ok: false,
      reason: "componentMustStartUppercase",
    });
  });
});

describe("open account entry", () => {
  it("builds one OPEN payload with a local ISO date and currency", () => {
    const date = new Date(2026, 6, 27, 23, 30);
    expect(
      buildOpenAccountEntry({
        account: "Assets:Bank:Checking",
        currencies: ["USD"],
        date,
      }),
    ).toEqual({
      type: "OPEN",
      open: {
        account: "Assets:Bank:Checking",
        currencies: ["USD"],
        date: "2026-07-27",
      },
    });
  });

  it("preserves an empty currencies list", () => {
    const entry = buildOpenAccountEntry({
      account: "Equity:Opening-Balances",
      currencies: [],
      date: new Date(2026, 0, 2),
    });

    expect(entry.open?.currencies).toEqual([]);
    expect(entry.open?.date).toBe("2026-01-02");
  });

  it("copies currencies instead of retaining mutable form state", () => {
    const currencies = ["USD"];
    const entry = buildOpenAccountEntry({
      account: "Assets:Bank:Checking",
      currencies,
      date: new Date(2026, 6, 27),
    });

    currencies.push("EUR");
    expect(entry.open?.currencies).toEqual(["USD"]);
  });
});

describe("typedSubPathIssue", () => {
  it("holds back a name that is still being typed", () => {
    expect(typedSubPathIssue("Investments:")).toBe("incomplete");
    expect(typedSubPathIssue("Bank:Checking: ")).toBe("incomplete");
  });

  it("names an empty component the composer would silently collapse", () => {
    expect(typedSubPathIssue("Bank::Checking")).toBe("emptyComponent");
    expect(typedSubPathIssue(":Bank")).toBe("emptyComponent");
  });

  it("accepts a complete name and leaves an empty field to the validator", () => {
    expect(typedSubPathIssue("Investments:Brokerage")).toBe(null);
    expect(typedSubPathIssue("Bank")).toBe(null);
    expect(typedSubPathIssue("")).toBe(null);
  });

  it("gates the form's submit, and its Return key, on the typed text", () => {
    const source = require("fs").readFileSync(
      require("path").join(
        __dirname,
        "..",
        "screens",
        "open-account-screen",
        "open-account-screen.tsx",
      ),
      "utf8",
    );
    expect(
      source.includes("const nameOk = validation.ok && typedIssue === null;"),
    ).toBe(true);
    expect(source.includes("openAccountSubmitState({")).toBe(true);
    expect(source.includes("openAccounts: meta?.accounts,")).toBe(true);
    expect(source.includes("busy: loading,")).toBe(true);
    expect(source.includes("onSubmitEditing={handleSubmit}")).toBe(true);
    expect(source.includes('t("openAccountNamePreview", { account })')).toBe(
      true,
    );
  });
});

describe("openAccountSubmitState", () => {
  // Open Account showed "Will be created as Assets:Bank:Checking" for an
  // account the ledger already opened, so Done wrote a duplicate `open`
  // directive and broke the ledger (w0/037).
  const open = ["Assets:Bank:Checking", "Expenses:Food", "Equity:Opening"];
  const state = (
    account: string,
    overrides: Partial<Parameters<typeof openAccountSubmitState>[0]> = {},
  ) =>
    openAccountSubmitState({
      account,
      nameOk: true,
      openAccounts: open,
      busy: false,
      ...overrides,
    });

  it("refuses an account the ledger already opens", () => {
    expect(state("Assets:Bank:Checking")).toEqual({
      canSubmit: false,
      alreadyOpen: true,
    });
  });

  it("allows a new account", () => {
    expect(state("Assets:Bank:Savings")).toEqual({
      canSubmit: true,
      alreadyOpen: false,
    });
  });

  it("treats a name differing only in case as a different account", () => {
    // Beancount account names are case-sensitive.
    expect(state("Assets:Bank:CHECKING")).toEqual({
      canSubmit: true,
      alreadyOpen: false,
    });
  });

  it("waits for the ledger's accounts before allowing any name", () => {
    expect(state("Assets:Bank:Savings", { openAccounts: undefined })).toEqual({
      canSubmit: false,
      alreadyOpen: false,
    });
  });

  it("allows a first account in an empty ledger", () => {
    expect(state("Assets:Cash", { openAccounts: [] })).toEqual({
      canSubmit: true,
      alreadyOpen: false,
    });
  });

  it("leaves an invalid or busy form to its own message", () => {
    expect(state("Assets:Bank:Checking", { nameOk: false })).toEqual({
      canSubmit: false,
      alreadyOpen: false,
    });
    expect(state("Assets:Bank:Savings", { busy: true })).toEqual({
      canSubmit: false,
      alreadyOpen: false,
    });
  });
});

// A full name typed or pasted into the sub-path used to compose under the
// selected root again: `Assets:Assets:Bank:Checking` (w21/004).
describe("peelTypedRoot", () => {
  it("moves a typed root into the selector for every root", () => {
    for (const root of ACCOUNT_ROOT_PREFIXES) {
      expect(peelTypedRoot(`${root}:Bank:Checking`, "Assets")).toEqual({
        rootPrefix: root,
        subPath: "Bank:Checking",
      });
    }
  });

  it("composes the real name, so the already-open check sees it", () => {
    const typed = peelTypedRoot("Assets:Bank:Checking", "Assets");
    const account = composeAccountName(typed.rootPrefix, typed.subPath);
    expect(account).toBe("Assets:Bank:Checking");
    expect(
      openAccountSubmitState({
        account,
        nameOk: true,
        openAccounts: ["Assets:Bank:Checking"],
        busy: false,
      }),
    ).toEqual({ alreadyOpen: true, canSubmit: false });
  });

  it("matches the root in any case and keeps the rest verbatim", () => {
    expect(peelTypedRoot("assets:Bank:X", "Expenses")).toEqual({
      rootPrefix: "Assets",
      subPath: "Bank:X",
    });
    // Lowercase components stay for validation to refuse.
    expect(peelTypedRoot("Liabilities:creditCard", "Assets")).toEqual({
      rootPrefix: "Liabilities",
      subPath: "creditCard",
    });
  });

  it("switches the selector as soon as a root and colon are typed", () => {
    expect(peelTypedRoot("Expenses:", "Assets")).toEqual({
      rootPrefix: "Expenses",
      subPath: "",
    });
  });

  it("leaves a root name later in the path, or with no colon yet, alone", () => {
    expect(peelTypedRoot("Bank:Assets", "Liabilities")).toEqual({
      rootPrefix: "Liabilities",
      subPath: "Bank:Assets",
    });
    expect(peelTypedRoot("Assets", "Equity")).toEqual({
      rootPrefix: "Equity",
      subPath: "Assets",
    });
    expect(peelTypedRoot("AssetsHeld:Gold", "Assets")).toEqual({
      rootPrefix: "Assets",
      subPath: "AssetsHeld:Gold",
    });
  });
});

describe("Open Account sub-path field", () => {
  it("peels a typed root on every change", () => {
    const source = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "screens",
        "open-account-screen",
        "open-account-screen.tsx",
      ),
      "utf8",
    );
    expect(source.includes("peelTypedRoot(value, rootPrefix)")).toBe(true);
  });
});

// w21/041: names the ledger opens, refused by the validator (the mobile
// counterpart of the dashboard's w4/279).
describe("validateAccountName: combining marks and titlecase initials", () => {
  const decomposed = "E\u0301pargne";

  it("accepts the names the ledger opens", () => {
    for (const name of [
      "Assets:Qa-20261020:हिंदी", // Devanagari with vowel signs
      `Assets:Qa-20261020:${decomposed}`, // a decomposed accent
      "Assets:Qa-20261020:Épargne", // a composed accent
      "Assets:Qa-20261020:ǅep", // a titlecase initial
      "Assets:Qa-20261020:Snacks",
    ])
      expect(validateAccountName(name)).toEqual({ ok: true });
  });

  it("still refuses what the ledger does not", () => {
    const cases: [string, AccountNameValidationReason][] = [
      ["bank:checking", "invalidRoot"],
      ["Assets:Bank:", "emptyComponent"],
      ["Assets:Bank:Chécking Acct", "invalidCharacters"],
      ["Assets:bank", "componentMustStartUppercase"],
      // A combining mark cannot start a component.
      ["Assets:\u0301Bank", "componentMustStartUppercase"],
    ];
    for (const [name, reason] of cases)
      expect(validateAccountName(name)).toEqual({ ok: false, reason });
  });

  it("writes a decomposed name composed", () => {
    const name = composeAccountName("Assets", `Qa:${decomposed}`);
    expect(name).toBe("Assets:Qa:Épargne");
    expect(name).toBe(name.normalize("NFC"));
  });
});
