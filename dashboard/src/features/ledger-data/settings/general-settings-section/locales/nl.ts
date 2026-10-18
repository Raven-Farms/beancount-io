export interface TranslationEntry {
  message: string;
  description: string;
}

const nlGeneralSettingsSection: Record<string, TranslationEntry> = {
  "page.settings.description": {
    message: "Beschrijving",
    description: "Label for ledger description field in settings",
  },
  "page.settings.settingsUpdated": {
    message: "Instellingen succesvol bijgewerkt",
    description: "Success message when settings are saved",
  },
  "page.settings.ledgerNameDescription": {
    message: "Deze naam wordt overal in de applicatie weergegeven",
    description: "Help text for ledger name field",
  },
  "page.settings.ledgerNameTaken": {
    message: "Er bestaat al een grootboek met de naam {name}.",
    description:
      "Rename refusal when another ledger of the same owner already has the name; {name} is the slug",
  },
  "page.settings.generalSettings": {
    message: "Algemene instellingen",
    description: "Section title for general settings",
  },
  "page.settings.generalSettingsDescription": {
    message: "Werk uw grootboeknaam en basisinformatie bij",
    description: "Description for general settings section",
  },
  "page.settings.ledgerDescriptionDescription": {
    message:
      "Deze beschrijving wordt gebruikt voor SEO-metatags en helpt anderen het doel van uw grootboek te begrijpen.",
    description: "Help text explaining the description field",
  },
  "page.settings.ledgerDescriptionPlaceholder": {
    message: "Voer een beschrijving in voor uw grootboek (optioneel)",
    description: "Placeholder text for description field",
  },
  "page.settings.generalSettingsDescriptionReadOnly": {
    message:
      "De naam en beschrijving van dit grootboek. Alleen beheerders van het grootboek kunnen ze wijzigen.",
    description:
      "General settings description shown to viewers who cannot edit the ledger",
  },
};

export default nlGeneralSettingsSection;
