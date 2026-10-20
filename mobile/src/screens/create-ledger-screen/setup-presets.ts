import type { LedgerSetupPreset } from "@/generated-graphql/types";

/**
 * The mobile copy of the setup catalog (ADR021): preset identities and
 * account names. The canonical catalog lives in backend-v2; the ledger's
 * accounting is always built server-side from the specification this
 * screen sends, never from this list.
 */
export interface SetupPreset {
  id: LedgerSetupPreset;
  titleKey: string;
  outcomeKey: string;
  accounts: { name: string; money: boolean }[];
}

const money = (name: string) => ({ name, money: true });
const category = (name: string) => ({ name, money: false });

export const SETUP_PRESETS: SetupPreset[] = [
  {
    id: "PERSONAL" as LedgerSetupPreset,
    titleKey: "createLedgerPresetPersonal",
    outcomeKey: "createLedgerPresetPersonalOutcome",
    accounts: [
      money("Assets:Cash"),
      money("Assets:Bank"),
      money("Liabilities:CreditCard"),
      money("Liabilities:Loan"),
      category("Income:General"),
      category("Expenses:Food"),
      category("Expenses:Housing"),
      category("Expenses:Transport"),
      category("Expenses:Utilities"),
      category("Expenses:Health"),
      category("Expenses:Other"),
      category("Equity:OpeningBalances"),
    ],
  },
  {
    id: "FREELANCE" as LedgerSetupPreset,
    titleKey: "createLedgerPresetFreelance",
    outcomeKey: "createLedgerPresetFreelanceOutcome",
    accounts: [
      money("Assets:Bank"),
      money("Assets:Cash"),
      money("Liabilities:CreditCard"),
      category("Income:Services"),
      category("Expenses:Software"),
      category("Expenses:Supplies"),
      category("Expenses:Travel"),
      category("Expenses:Fees"),
      category("Equity:OwnerContributions"),
      category("Equity:OwnerDrawings"),
    ],
  },
  {
    id: "BUSINESS" as LedgerSetupPreset,
    titleKey: "createLedgerPresetBusiness",
    outcomeKey: "createLedgerPresetBusinessOutcome",
    accounts: [
      money("Assets:Bank"),
      money("Assets:Cash"),
      category("Income:Sales"),
      category("Income:Services"),
      category("Expenses:Operating"),
      category("Equity:Capital"),
      category("Equity:RetainedEarnings"),
      category("Equity:OpeningBalances"),
    ],
  },
  {
    id: "PORTFOLIO" as LedgerSetupPreset,
    titleKey: "createLedgerPresetPortfolio",
    outcomeKey: "createLedgerPresetPortfolioOutcome",
    accounts: [
      money("Assets:BrokerCash"),
      money("Assets:Holdings"),
      category("Income:Dividends"),
      category("Income:Interest"),
      category("Expenses:Fees"),
      category("Equity:OpeningBalances"),
    ],
  },
  {
    id: "RENTAL" as LedgerSetupPreset,
    titleKey: "createLedgerPresetRental",
    outcomeKey: "createLedgerPresetRentalOutcome",
    accounts: [
      money("Assets:Bank"),
      money("Assets:Cash"),
      category("Income:Rent"),
      category("Expenses:Repairs"),
      category("Expenses:Insurance"),
      category("Expenses:Management"),
      category("Expenses:PropertyOther"),
      money("Liabilities:Deposits"),
      category("Equity:OpeningBalances"),
    ],
  },
  {
    id: "SHARED_EXPENSES" as LedgerSetupPreset,
    titleKey: "createLedgerPresetShared",
    outcomeKey: "createLedgerPresetSharedOutcome",
    accounts: [
      money("Assets:MemberReceivables"),
      money("Liabilities:MemberPayables"),
      category("Expenses:Shared"),
      category("Equity:OpeningBalances"),
    ],
  },
  {
    id: "COMMUNITY" as LedgerSetupPreset,
    titleKey: "createLedgerPresetCommunity",
    outcomeKey: "createLedgerPresetCommunityOutcome",
    accounts: [
      money("Assets:Cash"),
      money("Assets:Bank"),
      category("Income:Dues"),
      category("Income:Contributions"),
      category("Income:Events"),
      category("Expenses:Projects"),
      category("Expenses:Events"),
      category("Expenses:Administration"),
      category("Equity:OpeningBalances"),
    ],
  },
  {
    id: "BLANK" as LedgerSetupPreset,
    titleKey: "createLedgerPresetBlank",
    outcomeKey: "createLedgerPresetBlankOutcome",
    accounts: [],
  },
];

const EUROZONE = new Set([
  "AT",
  "BE",
  "CY",
  "DE",
  "EE",
  "ES",
  "FI",
  "FR",
  "GR",
  "HR",
  "IE",
  "IT",
  "LT",
  "LU",
  "LV",
  "MT",
  "NL",
  "PT",
  "SI",
  "SK",
]);

const REGION_CURRENCY: Record<string, string> = {
  US: "USD",
  GB: "GBP",
  JP: "JPY",
  CN: "CNY",
  AU: "AUD",
  CA: "CAD",
  CH: "CHF",
  NZ: "NZD",
  IN: "INR",
  BR: "BRL",
  KR: "KRW",
  MX: "MXN",
  ZA: "ZAR",
  SG: "SGD",
  HK: "HKD",
  SE: "SEK",
  NO: "NOK",
  DK: "DKK",
  PL: "PLN",
  TR: "TRY",
  ID: "IDR",
  TH: "THB",
};

/**
 * Suggest a currency from the device's region only (ADR021): the region
 * the OS reports for the locale, never its language. Falls back to USD.
 */
export function suggestCurrency(regionCode: string | null | undefined): string {
  const region = regionCode?.toUpperCase();
  if (!region || !/^[A-Z]{2}$/.test(region)) return "USD";
  if (EUROZONE.has(region)) return "EUR";
  return REGION_CURRENCY[region] ?? "USD";
}
