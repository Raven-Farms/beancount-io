export interface TranslationEntry {
  message: string;
  description: string;
}

const skGeneralSettingsSection: Record<string, TranslationEntry> = {
  "page.settings.description": {
    message: "Popis",
    description: "Label for ledger description field in settings",
  },
  "page.settings.settingsUpdated": {
    message: "Nastavenia boli úspešne aktualizované",
    description: "Success message when settings are saved",
  },
  "page.settings.ledgerNameDescription": {
    message: "Tento názov sa zobrazí v celej aplikácii",
    description: "Help text for ledger name field",
  },
  "page.settings.generalSettings": {
    message: "Všeobecné nastavenia",
    description: "Section title for general settings",
  },
  "page.settings.generalSettingsDescription": {
    message: "Aktualizujte názov vašej knihy a základné informácie",
    description: "Description for general settings section",
  },
  "page.settings.ledgerDescriptionDescription": {
    message:
      "Tento popis sa použije pre SEO meta značky a pomáha ostatným pochopiť účel vašej knihy.",
    description: "Help text explaining the description field",
  },
  "page.settings.ledgerDescriptionPlaceholder": {
    message: "Zadajte popis vašej knihy (voliteľné)",
    description: "Placeholder text for description field",
  },
  "page.settings.generalSettingsDescriptionReadOnly": {
    message:
      "Názov a popis tejto účtovnej knihy. Zmeniť ich môžu iba správcovia knihy.",
    description:
      "General settings description shown to viewers who cannot edit the ledger",
  },
};

export default skGeneralSettingsSection;
