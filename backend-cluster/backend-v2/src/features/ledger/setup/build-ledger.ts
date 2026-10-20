import { ValidationError } from "@/shared/errors";
import { presetById, setupCatalog, setupCurrencies } from "./index";


interface SetupAccountSelection {
  name: string;
  kind?: string;
  currency?: string;
  openingState?: string;
  /** Decimal string, required when `openingState` is "known". */
  amount?: string;
}

export interface LedgerSetup {
  preset: string;
  title?: string;
  operatingCurrency?: string;
  historyStart?: string;
  capabilities?: Record<string, string>;
  accounts?: SetupAccountSelection[];
}

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const AMOUNT_PATTERN = /^-?\d+(\.\d+)?$/;
const OPENING_EQUITY = "Equity:OpeningBalances";

const fail = (message: string): never => {
  throw new ValidationError(message, "setup");
};

const dayBefore = (date: string): string => {
  const parsed = new Date(`${date}T00:00:00Z`);
  parsed.setUTCDate(parsed.getUTCDate() - 1);
  return parsed.toISOString().slice(0, 10);
};

/**
 * Pure builder: turns a setup specification (ADR021) into ledger files.
 * Throws `ValidationError` for any invalid explicit value; nothing is
 * created by callers when it throws.
 */
export interface LedgerSetupPreview {
  preset: string;
  operatingCurrency: string;
  historyStart: string;
  accounts: string[];
  files: Record<string, string>;
}

export function buildLedgerFiles(
  setup: LedgerSetup,
  today: string = new Date().toISOString().slice(0, 10),
): Record<string, string> {
  return previewLedgerSetup(setup, today).files;
}

/** Preview a setup without creating anything: the files plus their summary. */
export function previewLedgerSetup(
  setup: LedgerSetup,
  today: string = new Date().toISOString().slice(0, 10),
): LedgerSetupPreview {
  const preset =
    presetById(setup.preset) ?? fail(`Unknown preset "${setup.preset}"`);

  const operatingCurrency = setup.operatingCurrency ?? "USD";
  if (!setupCurrencies.supportedCurrencies.includes(operatingCurrency)) {
    fail(`Unsupported operating currency "${operatingCurrency}"`);
  }

  const historyStart = setup.historyStart ?? today;
  if (!DATE_PATTERN.test(historyStart) || Number.isNaN(Date.parse(historyStart))) {
    fail(`Invalid history start "${historyStart}"`);
  }

  const capabilities = setup.capabilities ?? {};
  for (const [id, state] of Object.entries(capabilities)) {
    if (!(setupCatalog.capabilityStates as string[]).includes(state)) {
      fail(`Invalid capability state "${state}" for "${id}"`);
    }
    if (!preset.optionalQuestions.some((question) => question.id === id)) {
      fail(`Preset "${preset.id}" has no capability "${id}"`);
    }
  }

  const enabledAccounts = new Set<string>();
  for (const question of preset.optionalQuestions) {
    if (capabilities[question.id] === "enabled") {
      for (const name of question.enablesAccounts) enabledAccounts.add(name);
    }
  }

  const allowed = new Set<string>([
    ...preset.accounts.map((account) => account.name),
    ...enabledAccounts,
  ]);
  const isBlank = preset.id === "blank@1";

  // Preset accounts are opened with no balance claim: only an account the
  // customer explicitly selected carries an opening state, so an opened
  // account never reads as a verified zero the customer did not confirm.
  const selected = new Map<string, SetupAccountSelection>();
  for (const account of preset.accounts) {
    selected.set(account.name, { name: account.name });
  }
  for (const name of enabledAccounts) {
    if (!selected.has(name)) selected.set(name, { name });
  }
  for (const selection of setup.accounts ?? []) {
    if (!isBlank && !allowed.has(selection.name)) {
      fail(
        `Account "${selection.name}" is not part of preset "${preset.id}" or an enabled capability`,
      );
    }
    const openingState = selection.openingState ?? "unknown";
    if (!(setupCatalog.openingStates as string[]).includes(openingState)) {
      fail(`Invalid opening state "${openingState}" for "${selection.name}"`);
    }
    if (openingState === "known") {
      if (!selection.amount || !AMOUNT_PATTERN.test(selection.amount)) {
        fail(
          `Account "${selection.name}" needs a decimal amount for a known opening balance`,
        );
      }
    } else if (selection.amount !== undefined) {
      fail(
        `Account "${selection.name}" must not carry an amount unless its opening state is "known"`,
      );
    }
    if (selection.currency !== undefined && selection.currency !== operatingCurrency) {
      if (!setupCurrencies.supportedCurrencies.includes(selection.currency)) {
        fail(`Unsupported currency "${selection.currency}" for "${selection.name}"`);
      }
    }
    selected.set(selection.name, { ...selection, openingState });
  }

  // A known opening posts the day before the history boundary and asserts
  // on the boundary, so the accounts must already be open then: when any
  // known opening exists, every account opens the day before the boundary.
  const hasKnownOpening = [...selected.values()].some(
    (account) => account.openingState === "known",
  );
  const openDate = hasKnownOpening ? dayBefore(historyStart) : historyStart;

  const openingStatusKey = setupCatalog.metadataKeys.openingBalanceStatus;
  const lines: string[] = [
    `option "title" "${(setup.title ?? preset.title).replace(/"/g, "")}"`,
    `option "operating_currency" "${operatingCurrency}"`,
    `option "inferred_tolerance_default" "*:0.001"`,
    "",
    'plugin "beancount.plugins.auto_accounts"',
    "",
  ];

  const openings: string[] = [];
  const assertions: string[] = [];
  const accounts = [...selected.values()].sort((a, b) =>
    a.name.localeCompare(b.name),
  );
  for (const account of accounts) {
    const currency = account.currency ?? operatingCurrency;
    lines.push(`${openDate} open ${account.name} ${currency}`);
    if (account.openingState === "unknown") {
      lines.push(`  ${openingStatusKey}: "unknown"`);
    } else if (account.openingState === "zero") {
      lines.push(`  ${openingStatusKey}: "zero"`);
    }
    if (account.openingState === "known" && account.amount) {
      const amount = account.amount;
      const counter = account.name === OPENING_EQUITY ? null : OPENING_EQUITY;
      if (counter && !selected.has(counter)) {
        lines.push(`${openDate} open ${counter} ${currency}`);
        selected.set(counter, { name: counter });
      }
      if (counter) {
        const negated = amount.startsWith("-") ? amount.slice(1) : `-${amount}`;
        openings.push(
          `${dayBefore(historyStart)} * "Opening balance"`,
          `  ${account.name} ${amount} ${currency}`,
          `  ${counter} ${negated} ${currency}`,
          "",
        );
      }
      assertions.push(
        `${historyStart} balance ${account.name} ${amount} ${currency}`,
      );
    }
  }

  if (openings.length > 0) {
    lines.push("", ...openings);
  }
  if (assertions.length > 0) {
    lines.push(...assertions, "");
  }

  const openedAccounts = [
    ...new Set(
      lines
        .map((line) => line.match(/^\d{4}-\d{2}-\d{2} open (\S+)/)?.[1])
        .filter((name): name is string => Boolean(name)),
    ),
  ].sort();
  return {
    preset: preset.id,
    operatingCurrency,
    historyStart,
    accounts: openedAccounts,
    files: { "main.bean": `${lines.join("\n")}\n` },
  };
}
