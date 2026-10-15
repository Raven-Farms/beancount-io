export interface TranslationEntry {
  message: string;
  description: string;
}

const caGeneralSettingsSection: Record<string, TranslationEntry> = {
  "page.settings.description": {
    message: "Descripció",
    description: "Label for ledger description field in settings",
  },
  "page.settings.settingsUpdated": {
    message: "La configuració s'ha actualitzat correctament",
    description: "Success message when settings are saved",
  },
  "page.settings.ledgerNameDescription": {
    message: "Aquest nom es mostrarà a tota l'aplicació",
    description: "Help text for ledger name field",
  },
  "page.settings.generalSettings": {
    message: "Configuració general",
    description: "Section title for general settings",
  },
  "page.settings.generalSettingsDescription": {
    message: "Actualitza el nom del teu llibre i la informació bàsica",
    description: "Description for general settings section",
  },
  "page.settings.ledgerDescriptionDescription": {
    message:
      "Aquesta descripció s'utilitzarà per a les metaetiquetes SEO i ajuda els altres a entendre el propòsit del vostre llibre.",
    description: "Help text explaining the description field",
  },
  "page.settings.ledgerDescriptionPlaceholder": {
    message: "Introduïu una descripció per al vostre llibre (opcional)",
    description: "Placeholder text for description field",
  },
  "page.settings.generalSettingsDescriptionReadOnly": {
    message:
      "El nom i la descripció d'aquest llibre comptable. Només els administradors del llibre els poden canviar.",
    description:
      "General settings description shown to viewers who cannot edit the ledger",
  },
};

export default caGeneralSettingsSection;
