export interface TranslationEntry {
  message: string;
  description: string;
}

const ptGeneralSettingsSection: Record<string, TranslationEntry> = {
  "page.settings.description": {
    message: "Descrição",
    description: "Label for ledger description field in settings",
  },
  "page.settings.settingsUpdated": {
    message: "Configurações atualizadas com sucesso",
    description: "Success message when settings are saved",
  },
  "page.settings.ledgerNameDescription": {
    message: "Este nome será exibido em toda a aplicação",
    description: "Help text for ledger name field",
  },
  "page.settings.ledgerNameTaken": {
    message: "Já existe um livro chamado {name}.",
    description:
      "Rename refusal when another ledger of the same owner already has the name; {name} is the slug",
  },
  "page.settings.generalSettings": {
    message: "Configurações Gerais",
    description: "Section title for general settings",
  },
  "page.settings.generalSettingsDescription": {
    message: "Atualize o nome do seu livro-razão e informações básicas",
    description: "Description for general settings section",
  },
  "page.settings.ledgerDescriptionDescription": {
    message:
      "Esta descrição será usada nas meta tags de SEO e ajuda outras pessoas a entender o propósito do seu livro-razão.",
    description: "Help text explaining the description field",
  },
  "page.settings.ledgerDescriptionPlaceholder": {
    message: "Insira uma descrição para o seu livro-razão (opcional)",
    description: "Placeholder text for description field",
  },
  "page.settings.generalSettingsDescriptionReadOnly": {
    message:
      "O nome e a descrição deste livro-razão. Somente os administradores do livro podem alterá-los.",
    description:
      "General settings description shown to viewers who cannot edit the ledger",
  },
};

export default ptGeneralSettingsSection;
