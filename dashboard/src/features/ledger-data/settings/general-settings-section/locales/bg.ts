export interface TranslationEntry {
  message: string;
  description: string;
}

const bgGeneralSettingsSection: Record<string, TranslationEntry> = {
  "page.settings.description": {
    message: "Описание",
    description: "Label for ledger description field in settings",
  },
  "page.settings.settingsUpdated": {
    message: "Настройките са актуализирани успешно",
    description: "Success message when settings are saved",
  },
  "page.settings.ledgerNameDescription": {
    message: "Това име ще се показва в цялото приложение",
    description: "Help text for ledger name field",
  },
  "page.settings.generalSettings": {
    message: "Общи настройки",
    description: "Section title for general settings",
  },
  "page.settings.generalSettingsDescription": {
    message: "Актуализирайте името и основната информация на книгата",
    description: "Description for general settings section",
  },
  "page.settings.ledgerDescriptionDescription": {
    message:
      "Това описание ще се използва за SEO мета тагове и помага на другите да разберат предназначението на вашата книга.",
    description: "Help text explaining the description field",
  },
  "page.settings.ledgerDescriptionPlaceholder": {
    message: "Въведете описание на вашата книга (по избор)",
    description: "Placeholder text for description field",
  },
  "page.settings.generalSettingsDescriptionReadOnly": {
    message:
      "Името и описанието на тази счетоводна книга. Само администраторите на книгата могат да ги променят.",
    description:
      "General settings description shown to viewers who cannot edit the ledger",
  },
};

export default bgGeneralSettingsSection;
