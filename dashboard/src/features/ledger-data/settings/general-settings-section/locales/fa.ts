export interface TranslationEntry {
  message: string;
  description: string;
}

const faGeneralSettingsSection: Record<string, TranslationEntry> = {
  "page.settings.description": {
    message: "توضیحات",
    description: "Label for ledger description field in settings",
  },
  "page.settings.settingsUpdated": {
    message: "تنظیمات با موفقیت به‌روزرسانی شد",
    description: "Success message when settings are saved",
  },
  "page.settings.ledgerNameDescription": {
    message: "این نام در سراسر برنامه نمایش داده خواهد شد",
    description: "Help text for ledger name field",
  },
  "page.settings.generalSettings": {
    message: "تنظیمات عمومی",
    description: "Section title for general settings",
  },
  "page.settings.generalSettingsDescription": {
    message: "نام دفتر و اطلاعات پایه خود را به‌روزرسانی کنید",
    description: "Description for general settings section",
  },
  "page.settings.ledgerDescriptionDescription": {
    message:
      "این توضیحات برای متاتگ‌های SEO استفاده می‌شود و به دیگران کمک می‌کند هدف دفتر شما را درک کنند.",
    description: "Help text explaining the description field",
  },
  "page.settings.ledgerDescriptionPlaceholder": {
    message: "توضیحاتی برای دفتر خود وارد کنید (اختیاری)",
    description: "Placeholder text for description field",
  },
  "page.settings.generalSettingsDescriptionReadOnly": {
    message:
      "نام و توضیحات این دفتر. فقط مدیران دفتر می‌توانند آن‌ها را تغییر دهند.",
    description:
      "General settings description shown to viewers who cannot edit the ledger",
  },
};

export default faGeneralSettingsSection;
