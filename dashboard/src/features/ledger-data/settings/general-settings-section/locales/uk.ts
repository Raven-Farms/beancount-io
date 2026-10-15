export interface TranslationEntry {
  message: string;
  description: string;
}

const ukGeneralSettingsSection: Record<string, TranslationEntry> = {
  "page.settings.description": {
    message: "Опис",
    description: "Label for ledger description field in settings",
  },
  "page.settings.settingsUpdated": {
    message: "Налаштування успішно оновлено",
    description: "Success message when settings are saved",
  },
  "page.settings.ledgerNameDescription": {
    message: "Ця назва буде відображатися в усьому додатку",
    description: "Help text for ledger name field",
  },
  "page.settings.generalSettings": {
    message: "Загальні налаштування",
    description: "Section title for general settings",
  },
  "page.settings.generalSettingsDescription": {
    message: "Оновіть назву вашої книги та основну інформацію",
    description: "Description for general settings section",
  },
  "page.settings.ledgerDescriptionDescription": {
    message:
      "Цей опис використовуватиметься для SEO мета-тегів і допомагає іншим зрозуміти призначення вашої книги.",
    description: "Help text explaining the description field",
  },
  "page.settings.ledgerDescriptionPlaceholder": {
    message: "Введіть опис вашої книги (необов'язково)",
    description: "Placeholder text for description field",
  },
  "page.settings.generalSettingsDescriptionReadOnly": {
    message:
      "Назва та опис цієї облікової книги. Змінити їх можуть лише адміністратори книги.",
    description:
      "General settings description shown to viewers who cannot edit the ledger",
  },
};

export default ukGeneralSettingsSection;
