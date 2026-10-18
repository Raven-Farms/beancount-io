import { apiKeyTranslations } from "../pages/api-keys/translations";

export interface TranslationEntry {
  message: string;
  description: string;
}

const bgUserSettings: Record<string, TranslationEntry> = {
  ...apiKeyTranslations.bg,
  "userSettings.accessUntil": {
    message: "Достъп до",
    description: "Label for access remaining until date",
  },
  "userSettings.accountDeleted": {
    message: "Акаунтът е изтрит успешно",
    description: "Success message when account is deleted",
  },
  "userSettings.addNewKey": {
    message: "Добавяне на нов ключ",
    description: "Button text to add new key",
  },
  "userSettings.added": {
    message: "Добавен",
    description: "Label for when key was added",
  },
  "userSettings.allDocumentsAndAttachments": {
    message: "Всички качени документи и прикачени файлове",
    description: "Item in delete account list",
  },
  "userSettings.allLedgersAndTransactions": {
    message: "Всички ваши книги и история на транзакции",
    description: "Item in delete account list",
  },
  "userSettings.allPreferencesAndSettings": {
    message: "Всички предпочитания и настройки",
    description: "Item in delete account list",
  },
  "userSettings.allTransactionsAndRecords": {
    message: "Всички транзакции и записи",
    description: "Item in delete account list",
  },
  "userSettings.appearance": {
    message: "Външен вид",
    description: "Appearance settings section label",
  },
  "userSettings.cancelSubscription": {
    message: "Отказ на абонамент",
    description: "Button text to cancel subscription",
  },
  "userSettings.cancelSubscriptionDescription": {
    message:
      "Сигурни ли сте, че искате да откажете абонамента си? Ще продължите да имате достъп до края на текущия си платежен период.",
    description: "Confirmation dialog description for canceling subscription",
  },
  "userSettings.cancelSubscriptionTitle": {
    message: "Отказ на абонамент?",
    description: "Confirmation dialog title for canceling subscription",
  },
  "userSettings.canceling": {
    message: "Отказване...",
    description: "Button text while canceling subscription",
  },
  "userSettings.cannotBeUndone": {
    message: "Това действие не може да бъде отменено.",
    description: "Warning that action is irreversible",
  },
  "userSettings.changeName": {
    message: "Промяна на име",
    description: "Dialog title for changing name",
  },
  "userSettings.changeUsername": {
    message: "Промяна на потребителското име",
    description: "Dialog title for changing username",
  },
  "userSettings.confirmCancel": {
    message: "Да, откажи абонамента",
    description: "Button text to confirm subscription cancellation",
  },
  "userSettings.createKey": {
    message: "Създаване на ключ",
    description: "Button text to create key",
  },
  "userSettings.createNewApiKey": {
    message: "Създаване на нов SSH ключ",
    description: "Dialog title for creating an SSH public key",
  },
  "userSettings.createNewApiKeyDescription": {
    message: "Добавете нов публичен SSH ключ за достъп до Git хранилището.",
    description:
      "Dialog description for creating an SSH public key for Git access",
  },
  "userSettings.createNewKey": {
    message: "Създаване на нов ключ",
    description: "Button text to create new key",
  },
  "userSettings.creating": {
    message: "Създаване...",
    description: "Button text while creating key",
  },
  "userSettings.currentLanguage": {
    message: "Език",
    description: "Label showing current language selection",
  },
  "userSettings.customizeAppearance": {
    message: "Персонализиране на външния вид и поведението на приложението",
    description: "Description for appearance settings",
  },
  "userSettings.dangerZone": {
    message: "Опасна зона",
    description: "Section title for dangerous account actions",
  },
  "userSettings.dark": {
    message: "Тъмна",
    description: "Dark theme option",
  },
  "userSettings.deleteAccount": {
    message: "Изтриване на акаунт",
    description: "Button or menu item to delete user account",
  },
  "userSettings.deleteAccountConfirmMessage": {
    message:
      'За потвърждение, въведете вашето потребителско име "{username}" по-долу:',
    description:
      "Instructions for confirming account deletion by typing username",
  },
  "userSettings.deleteAccountConfirmPlaceholder": {
    message: "Въведете вашето потребителско име",
    description: "Placeholder text for deletion confirmation input",
  },
  "userSettings.deleteAccountDialogDescription": {
    message:
      "Това действие не може да бъде отменено. Това ще изтрие окончателно вашия акаунт и ще премахне всички ваши данни от нашите сървъри.",
    description: "Detailed warning in delete account dialog",
  },
  "userSettings.deleteAccountQuestion": {
    message: "Изтриване на акаунт?",
    description: "Dialog title confirming account deletion",
  },
  "userSettings.deleteAccountWarning": {
    message:
      "Окончателно изтриване на вашия акаунт и всички свързани данни. Това действие не може да бъде отменено.",
    description: "Warning text for account deletion",
  },
  "userSettings.deleteKey": {
    message: "Изтриване на ключ",
    description: "Button text to delete key",
  },
  "userSettings.deleteSshKey": {
    message: "Изтриване на SSH ключ",
    description: "Dialog title for deleting SSH key",
  },
  "userSettings.deleteSshKeyConfirmation": {
    message: "Сигурни ли сте, че искате да изтриете ключа",
    description: "Confirmation message for deleting SSH key",
  },
  "userSettings.deletingKey": {
    message: "Изтриване...",
    description: "Button text while deleting key",
  },
  "userSettings.enterNewName": {
    message: "Въведете вашето име по-долу",
    description: "Instructions in change name dialog",
  },
  "userSettings.enterNewUsername": {
    message: "Въведете новото си потребителско име по-долу",
    description: "Instructions in change username dialog",
  },
  "userSettings.enterNewUsernamePlaceholder": {
    message: "Въведете ново потребителско име",
    description: "Placeholder for new username input",
  },
  "userSettings.errorCreatingKey": {
    message: "Грешка при създаване на ключ",
    description: "Error title when key creation fails",
  },
  "userSettings.errorLoadingSettings": {
    message: "Грешка при зареждане на настройки",
    description: "Error message when settings fail to load",
  },
  "userSettings.failedToCancelSubscription": {
    message: "Неуспешно отказване на абонамент",
    description: "Error message when canceling subscription fails",
  },
  "userSettings.resumeSubscription": {
    message: "Възобновяване на абонамент",
    description: "Button text to resume a subscription scheduled to cancel",
  },
  "userSettings.resumeSubscriptionTitle": {
    message: "Възобновяване на абонамента?",
    description: "Confirmation dialog title for resuming subscription",
  },
  "userSettings.resumeSubscriptionDescription": {
    message:
      "Сигурни ли сте, че искате да възобновите абонамента си? Абонаментът ви ще продължи да се подновява автоматично и ще бъдете таксувани отново в края на текущия период на фактуриране.",
    description: "Confirmation dialog description for resuming subscription",
  },
  "userSettings.confirmResume": {
    message: "Да, възобновяване на абонамента",
    description: "Button text to confirm subscription resumption",
  },
  "userSettings.resuming": {
    message: "Възобновяване...",
    description: "Button text while resuming subscription",
  },
  "userSettings.subscriptionResumedSuccess": {
    message: "Абонаментът е възобновен успешно",
    description: "Success message after resuming subscription",
  },
  "userSettings.failedToResumeSubscription": {
    message: "Неуспешно възобновяване на абонамент",
    description: "Error message when resuming subscription fails",
  },
  "userSettings.failedToCreateCheckoutSession": {
    message: "Неуспешно създаване на сесия за плащане. Моля, опитайте отново.",
    description: "Error message when creating checkout session fails",
  },
  "userSettings.failedToLoadKeys": {
    message: "Неуспешно зареждане на ключове",
    description: "Error title when keys fail to load",
  },
  "userSettings.failedToLoadKeysDescription": {
    message:
      "Възникна грешка при зареждането на вашите SSH ключове. Моля, опитайте отново.",
    description: "Error description when keys fail to load",
  },
  "userSettings.failedToLoadSettings": {
    message: "Неуспешно зареждане на настройки",
    description: "Error heading when settings page fails",
  },
  "userSettings.failedToLoadSubscription": {
    message: "Неуспешно зареждане на състоянието на абонамента",
    description: "Error message when subscription fails to load",
  },
  "userSettings.firstName": {
    message: "Име",
    description: "Label for first name field",
  },
  "userSettings.followingWillBeDeleted": {
    message: "Следното ще бъде окончателно изтрито:",
    description: "Heading before list of items to be deleted",
  },
  "userSettings.general": {
    message: "Общи",
    description: "General settings section label",
  },
  "userSettings.invite": {
    message: "Покани",
    description: "Invite action button",
  },
  "userSettings.irreversibleActions": {
    message: "Необратими и разрушителни действия",
    description: "Description for danger zone",
  },
  "userSettings.keyTitle": {
    message: "Заглавие на ключа",
    description: "Label for key title field",
  },
  "userSettings.keyTitleDescription": {
    message:
      "Описателно име за този ключ, което да ви помогне да го идентифицирате по-късно.",
    description: "Description for key title field",
  },
  "userSettings.keyTitlePlaceholder": {
    message: "напр., Моят развоен ключ",
    description: "Placeholder for key title input",
  },
  "userSettings.lastName": {
    message: "Фамилия",
    description: "Label for last name field",
  },
  "userSettings.lastUsed3Months": {
    message: "Последно използван през последните 3 месеца",
    description: "Status when key was used within last 3 months",
  },
  "userSettings.lastUsed3Weeks": {
    message: "Последно използван през последните 3 седмици",
    description: "Status when key was used within last 3 weeks",
  },
  "userSettings.lastUsedLongAgo": {
    message: "Последно използван преди повече от 3 месеца",
    description: "Status when key was used long ago",
  },
  "userSettings.lastUsedWeek": {
    message: "Последно използван през последната седмица",
    description: "Status when key was used within last week",
  },
  "userSettings.light": {
    message: "Светла",
    description: "Light theme option",
  },
  "userSettings.loadingAccountInformation": {
    message: "Зареждане на информацията за вашия акаунт...",
    description: "Loading message for account information",
  },
  "userSettings.loadingSessionInformation": {
    message: "Зареждане на информацията за сесията...",
    description: "Loading message for session data",
  },
  "userSettings.loadingSshKeys": {
    message: "Зареждане на вашите SSH ключове...",
    description: "Loading state message for SSH keys",
  },
  "userSettings.loadingSubscriptionDetails": {
    message: "Зареждане на детайлите за абонамента...",
    description: "Loading message for subscription info",
  },
  "userSettings.loadingThemePreferences": {
    message: "Зареждане на предпочитанията за тема...",
    description: "Loading message for theme settings",
  },
  "userSettings.manageActiveSession": {
    message: "Управление на вашата активна сесия",
    description: "Description for session section",
  },
  "userSettings.manageBilling": {
    message: "Управление на плащания",
    description: "Button text to manage billing portal",
  },
  "userSettings.manageSubscription": {
    message: "Управление на вашия абонамент и плащания",
    description: "Description for subscription section",
  },
  "userSettings.monthly": {
    message: "Месечно",
    description: "Monthly frequency option",
  },
  "userSettings.name": {
    message: "Име",
    description: "Label for combined name field",
  },
  "userSettings.neverUsed": {
    message: "Никога не е използван",
    description: "Status when key has never been used",
  },
  "userSettings.newSshKey": {
    message: "Нов SSH ключ",
    description: "Button text to create new SSH key",
  },
  "userSettings.noSshKeys": {
    message: "Няма SSH ключове",
    description: "Empty state title when no SSH keys exist",
  },
  "userSettings.noSshKeysDescription": {
    message:
      "Все още не сте създали SSH ключове. Създайте първия си ключ, за да започнете с сигурен достъп до хранилището.",
    description: "Empty state description for SSH keys",
  },
  "userSettings.notSet": {
    message: "Не е зададено",
    description: "Placeholder when a field has no value",
  },
  "userSettings.opening": {
    message: "Отваряне...",
    description: "Button text while opening billing portal",
  },
  "userSettings.publicKey": {
    message: "Публичен ключ",
    description: "Label for public key field",
  },
  "userSettings.publicKeyDescription": {
    message:
      "Поставете тук публичния си ключ. Обикновено започва с ssh-ed25519 или ssh-rsa; можете да го изведете с cat ~/.ssh/id_ed25519.pub. Приемат се и публични ключове във формат PEM.",
    description: "Description for public key field",
  },
  "userSettings.publicKeyPlaceholder": {
    message: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA…",
    description: "Placeholder for public key textarea",
  },
  "userSettings.publicKeyRequired": {
    message: "Публичният ключ е задължителен",
    description: "Validation error for missing public key",
  },
  "userSettings.renewsOn": {
    message: "Подновява се на",
    description: "Label for subscription renewal date",
  },
  "userSettings.selectColorTheme": {
    message: "Изберете предпочитаната от вас цветна тема",
    description: "Label for theme selection",
  },
  "userSettings.selectLanguage": {
    message: "Изберете предпочитания от вас език",
    description: "Label for language selection",
  },
  "userSettings.session": {
    message: "Сесия",
    description: "Session management section title",
  },
  "userSettings.signOutDescription": {
    message: "Излезте от акаунта си и изчистете сесията си.",
    description: "Description for logout action",
  },
  "userSettings.sshKeys": {
    message: "SSH ключове",
    description: "Page title for SSH keys",
  },
  "userSettings.subscription": {
    message: "Абонамент",
    description: "Subscription section title",
  },
  "userSettings.subscriptionCanceled": {
    message: "Абонаментът е отказан",
    description: "Message when subscription is already canceled",
  },
  "userSettings.subscriptionCanceledSuccess": {
    message: "Абонаментът е отказан успешно",
    description: "Success message after canceling subscription",
  },
  "userSettings.subscriptionUpgraded": {
    message: "Абонаментът е обновен успешно",
    description: "Success message after upgrading subscription",
  },
  "userSettings.system": {
    message: "Системна",
    description: "System theme option",
  },
  "userSettings.theme": {
    message: "Тема",
    description: "Label for theme selection",
  },
  "userSettings.themeDark": {
    message: "Тъмна",
    description: "Dark theme option",
  },
  "userSettings.themeLight": {
    message: "Светла",
    description: "Light theme option",
  },
  "userSettings.themeSystem": {
    message: "Системна",
    description: "System theme option (follows OS preference)",
  },
  "userSettings.titleMaxLength": {
    message: "Заглавието трябва да бъде по-малко от 100 символа",
    description: "Validation error for title too long",
  },
  "userSettings.titleRequired": {
    message: "Заглавието е задължително",
    description: "Validation error for missing title",
  },
  "userSettings.unableToOpenBillingPortal": {
    message:
      "Невъзможно е да се отвори порталът за плащания. Моля, опитайте отново по-късно.",
    description: "Error message when billing portal fails to open",
  },
  "userSettings.unknownPlan": {
    message: "Неизвестен план",
    description: "Fallback when plan name is not available",
  },
  "userSettings.userProfile": {
    message: "Потребителски профил",
    description: "Section title for user profile settings",
  },
  "userSettings.usernameUpdatedSuccess": {
    message: "Потребителското име е актуализирано успешно",
    description: "Success message after updating username",
  },
  "userSettings.weekly": {
    message: "Седмично",
    description: "Weekly frequency option",
  },
  "userSettings.yesDeleteMyAccount": {
    message: "Да, изтрий моя акаунт",
    description: "Confirmation button for account deletion",
  },
  "userSettings.yourAccountInformation": {
    message: "Информацията за вашия акаунт",
    description: "Description for user profile section",
  },
  "userSettings.aiCfoUsage": {
    message: "AI токени",
    description: "Label for AI CFO usage section",
  },
  "userSettings.aiCfoUsageCount": {
    message: "{used} / {max} токена използвани този месец",
    description: "AI CFO usage count display",
  },
  "userSettings.aiCfoUsageUnlimited": {
    message: "{used} токена използвани този месец (неограничено)",
    description: "AI CFO usage display for unlimited tier",
  },
  "userSettings.currentPlan": {
    message: "Текущ план",
    description: "Badge label for the user's current subscription tier",
  },
  "userSettings.freePlan": {
    message: "Безплатен план",
    description: "Display name for the free tier",
  },
  "userSettings.enterprisePlan": {
    message: "Корпоративен",
    description: "Display name for the enterprise tier",
  },
  "userSettings.usage": {
    message: "Използване",
    description: "Section header for usage overview",
  },
  "userSettings.ledgers": {
    message: "Книги",
    description: "Label for ledger usage metric",
  },
  "userSettings.ledgerUsageCount": {
    message: "{used} / {max} книги",
    description: "Ledger usage count display",
  },
  "userSettings.billing": {
    message: "Фактуриране",
    description: "Section header for billing management",
  },
  "userSettings.unlimited": {
    message: "Неограничено",
    description: "Label for unlimited usage",
  },
  "userSettings.perMonth": {
    message: "/месец",
    description: "Price interval suffix",
  },
  "userSettings.aiTokensPerMonth": {
    message: "{count} AI токени / месец",
    description: "AI token allowance for a subscription tier",
  },
  "userSettings.unlimitedLedgers": {
    message: "Неограничени счетоводни книги",
    description: "Unlimited ledger allowance",
  },
  "userSettings.includedLedgers": {
    message: "{formattedCount} книги",
    description:
      "Ledger allowance for a subscription tier - interpolation: {formattedCount} is the count formatted in the app language; {count} selects the plural form (base key for pluralization)",
  },
  "userSettings.includedLedgers_one": {
    message: "{formattedCount} книга",
    description:
      "Ledger allowance for a subscription tier - interpolation: {formattedCount} is the count formatted in the app language; {count} selects the plural form - singular form",
  },
  "userSettings.includedLedgers_other": {
    message: "{formattedCount} книги",
    description:
      "Ledger allowance for a subscription tier - interpolation: {formattedCount} is the count formatted in the app language; {count} selects the plural form - plural form",
  },
  "userSettings.unlimitedDirectives": {
    message: "Неограничени директиви",
    description: "Unlimited directive allowance",
  },
  "userSettings.includedDirectives": {
    message: "{count} директиви",
    description: "Directive allowance for a subscription tier",
  },
  "userSettings.unlimitedCollaborators": {
    message: "Неограничен брой сътрудници",
    description: "Unlimited collaborator allowance",
  },
  "userSettings.collaboratorsPerLedger": {
    message: "До {formattedCount} сътрудници на книга",
    description:
      "Collaborator allowance for each ledger - interpolation: {formattedCount} is the count formatted in the app language; {count} selects the plural form (base key for pluralization)",
  },
  "userSettings.collaboratorsPerLedger_one": {
    message: "До {formattedCount} сътрудник на книга",
    description:
      "Collaborator allowance for each ledger - interpolation: {formattedCount} is the count formatted in the app language; {count} selects the plural form - singular form",
  },
  "userSettings.collaboratorsPerLedger_other": {
    message: "До {formattedCount} сътрудници на книга",
    description:
      "Collaborator allowance for each ledger - interpolation: {formattedCount} is the count formatted in the app language; {count} selects the plural form - plural form",
  },
  "userSettings.aiUsageUpgradeNudge": {
    message:
      "Използвате {percentage}% от месечните си AI токени. Надстройте, за да избегнете прекъсвания.",
    description: "Upgrade suggestion when AI token usage is high",
  },
  "userSettings.fingerprint": {
    message: "пръстов отпечатък",
    description: "Label for an SSH key fingerprint",
  },
  "userSettings.yearly": {
    message: "Годишно",
    description: "Yearly billing option in the billing-cycle toggle",
  },
  "userSettings.billingCycle": {
    message: "Период на плащане",
    description: "Accessible label for the monthly/yearly billing-cycle toggle",
  },
  "userSettings.plans": {
    message: "Планове",
    description: "Section header above every plan on the Billing page",
  },
  "userSettings.switchToYearly": {
    message: "Премини към годишно плащане",
    description: "Button that moves a monthly subscription to yearly billing",
  },
  "userSettings.switchToMonthly": {
    message: "Премини към месечно плащане",
    description: "Button that moves a yearly subscription to monthly billing",
  },
  "userSettings.downgrade": {
    message: "Понижи плана",
    description: "Button for moving to a lower plan",
  },
  "userSettings.contactUs": {
    message: "Свържете се с нас",
    description: "Enterprise plan call to action and price label",
  },
  "userSettings.renewalChangesComingSoon": {
    message:
      "Промените, които започват при подновяване, ще бъдат налични скоро.",
    description:
      "Hint under a plan change that takes effect at renewal, which is not available yet",
  },
  "userSettings.billedYearly": {
    message: "{amount} при годишно плащане",
    description: "Total charged once a year; {amount} is a formatted price",
  },
  "userSettings.saveYearlyPercent": {
    message: "Спестете {percent}%",
    description: "Badge with the yearly saving; {percent} is a whole number",
  },
  "userSettings.payYearlyOffer": {
    message:
      "Плащайте годишно: {yearly} на година вместо {monthlyTotal} — спестявате {saving} годишно.",
    description:
      "Offer on a monthly plan; {yearly}, {monthlyTotal} and {saving} are formatted prices",
  },
  "userSettings.perYear": {
    message: "/година",
    description: "Price interval suffix for yearly prices",
  },
  "userSettings.legacyPrice": {
    message: "Предишна цена",
    description: "Label for an older price an existing subscriber keeps",
  },
  "userSettings.checkoutConfirming": {
    message: "Потвърждаваме плащането ви…",
    description:
      "Shown while waiting for Stripe to confirm a just-completed checkout",
  },
  "userSettings.checkoutDone": {
    message: "Вече използвате {plan}",
    description:
      "Confirmation after checkout; {plan} is a plan name and billing cycle such as 'Premium \u00b7 Yearly'",
  },
  "userSettings.checkoutRenews": {
    message:
      "Подновява се на {date} за {amount}. Разписката ще получите по имейл.",
    description:
      "Renewal line after checkout; {date} is a formatted date and {amount} a formatted price",
  },
  "userSettings.checkoutUnlocked": {
    message: "Вече включва: {limits}",
    description: "What the new plan includes; {limits} is a list of quotas",
  },
  "userSettings.checkoutPending": {
    message:
      "Плащането е получено. Планът ви ще се появи до минута; обновете, за да проверите.",
    description:
      "Shown when the payment is done but the subscription is not recorded yet",
  },
  "userSettings.refresh": {
    message: "Обнови",
    description: "Button that reloads the subscription status",
  },
  "userSettings.backToWork": {
    message: "Обратно към предишната страница",
    description: "Button that returns to the page where the purchase began",
  },
  "userSettings.viewBilling": {
    message: "Към плащанията",
    description:
      "Button that closes the checkout confirmation and shows billing settings",
  },
  "userSettings.planChangeTitle": {
    message: "Промяна към {plan}",
    description:
      "Title of the plan-change sheet; {plan} is a plan and cycle such as 'Premium \u00b7 Yearly'",
  },
  "userSettings.planChangePreviewing": {
    message: "Изчисляваме цената на тази промяна…",
    description: "Shown while the server prices a plan change",
  },
  "userSettings.planChangePreviewFailed": {
    message: "Не успяхме да изчислим цената на промяната. Опитайте отново.",
    description: "Shown when the plan-change price could not be loaded",
  },
  "userSettings.planChangeStartsToday": {
    message: "Започва днес.",
    description: "The plan change takes effect immediately",
  },
  "userSettings.planChangeDueToday": {
    message: "Дължимо днес",
    description: "Label for the amount charged today",
  },
  "userSettings.planChangeCredit": {
    message:
      "Включва кредит от {credit} за неизползваното време от текущия план.",
    description: "Credit for unused time; {credit} is a formatted price",
  },
  "userSettings.planChangeNext": {
    message: "След това {amount}, следващо плащане на {date}.",
    description:
      "Next charge; {amount} is a price with its interval and {date} a formatted date",
  },
  "userSettings.planChangeChargedTo": {
    message: "Плаща се с {card}",
    description:
      "Card the change is charged to; {card} is a card brand and its last four digits",
  },
  "userSettings.planChangeWhatYouGet": {
    message: "Какво получавате",
    description: "Heading above what the new plan adds",
  },
  "userSettings.planChangePayAndSwitch": {
    message: "Платете {amount} и сменете",
    description:
      "Confirm button; {amount} is the formatted amount charged today",
  },
  "userSettings.planChangeContinueToCheckout": {
    message: "Към плащането",
    description: "Confirm button that opens Stripe Checkout",
  },
  "userSettings.planChangeNotNow": {
    message: "Не сега",
    description:
      "Button that closes the plan-change sheet without changing anything",
  },
  "userSettings.planChangeCreditNote": {
    message:
      "Неизползваното време винаги се приспада — никога не плащате два пъти.",
    description: "Reassurance under the confirm button",
  },
  "userSettings.planChangeRefusalCurrent": {
    message: "Вече използвате този план.",
    description: "The chosen plan is the one the customer already has",
  },
  "userSettings.planChangeRefusalSameTier": {
    message:
      "Запазвате този план на по-стара и по-ниска цена; смяната само би я повишила.",
    description:
      "The customer keeps an older, cheaper price for the same plan and cycle",
  },
  "userSettings.planChangeRefusalMultiple": {
    message:
      "Акаунтът ви има повече от един активен абонамент. Свържете се с поддръжката, за да смените плана.",
    description: "The account has duplicate subscriptions and needs support",
  },
  "userSettings.planChangeRefusalNoSubscription": {
    message:
      "Няма активен абонамент за промяна. Презаредете страницата, за да изберете план.",
    description: "The subscription ended before the change was confirmed",
  },
  "userSettings.planChangeRequiresAction": {
    message:
      "Банката ви трябва да одобри това плащане. Нищо не се променя преди това; след одобрението обновете страницата.",
    description: "The bank must approve the payment before the change applies",
  },
  "userSettings.planChangeApprovePayment": {
    message: "Одобрете плащането",
    description: "Button that opens Stripe's page to approve the payment",
  },
  "userSettings.planChangeFailed": {
    message: "Банката ви не одобри плащането. Нищо не е променено.",
    description: "The payment was declined and the plan did not change",
  },
  "userSettings.planChangeUseAnotherCard": {
    message: "Използвайте друга карта",
    description: "Button that opens billing settings to change the card",
  },
  "userSettings.featureAutomaticBackups": {
    message: "Автоматични резервни копия",
    description: "Plan feature from the pricing table",
  },
  "userSettings.featureAutomationIntegrations": {
    message: "Разширена автоматизация и интеграции",
    description: "Plan feature from the pricing table",
  },
  "userSettings.featureOidcSso": {
    message: "Единен вход (SSO) чрез OIDC",
    description:
      "Plan feature from the pricing table; OIDC and SSO stay as written",
  },
  "userSettings.featureMultiEntity": {
    message: "Консолидация на няколко юридически лица",
    description: "Plan feature from the pricing table",
  },
};

export default bgUserSettings;
