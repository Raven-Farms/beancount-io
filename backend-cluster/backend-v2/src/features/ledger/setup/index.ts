import catalogJson from "./catalog.json";
import currenciesJson from "./currencies.json";
import fixturesJson from "./fixtures.json";

type CapabilityState = "enabled" | "declined" | "deferred";
type OpeningState = "unknown" | "zero" | "known";

interface SetupCatalogAccount {
  name: string;
  kind: string;
  required: boolean;
}

interface SetupCatalogQuestion {
  id: string;
  prompt: string;
  effect: string;
  enablesAccounts: string[];
}

export interface SetupPreset {
  id: string;
  version: number;
  title: string;
  outcome: string;
  accounts: SetupCatalogAccount[];
  optionalQuestions: SetupCatalogQuestion[];
  categoryMeanings: Record<string, string>;
  evidenceRequirements: string[];
  firstResult: string;
  teachingExamples: string[];
  acceptanceScenario: {
    given: string;
    action: string;
    expected: Record<string, string>;
  };
}

export interface SetupCatalog {
  catalogVersion: number;
  source: string;
  metadataKeys: Record<string, string>;
  capabilityStates: CapabilityState[];
  openingStates: OpeningState[];
  presets: SetupPreset[];
}

export interface SetupCurrencies {
  source: Record<string, string>;
  supportedCurrencies: string[];
  regionCurrency: Record<string, string>;
}

export const setupCatalog = catalogJson as unknown as SetupCatalog;
export const setupCurrencies = currenciesJson as unknown as SetupCurrencies;
export const setupFixtures = fixturesJson.fixtures;

export const presetById = (id: string): SetupPreset | undefined =>
  setupCatalog.presets.find((preset) => preset.id === id);
