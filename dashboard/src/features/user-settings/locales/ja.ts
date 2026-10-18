import type { TranslationEntry } from "@/i18n";
import { apiKeyTranslations } from "../pages/api-keys/translations";

const jaUserSettings: Record<string, TranslationEntry> = {
  ...apiKeyTranslations.ja,
  "userSettings.accessUntil": {
    message: "アクセス期限",
    description: "Label for access remaining until date",
  },
  "userSettings.accountDeleted": {
    message: "アカウントが正常に削除されました",
    description: "Success message when account is deleted",
  },
  "userSettings.addNewKey": {
    message: "新しいキーを追加",
    description: "Button text to add new key",
  },
  "userSettings.added": {
    message: "追加済み",
    description: "Label for when key was added",
  },
  "userSettings.allDocumentsAndAttachments": {
    message: "アップロードされたすべてのドキュメントと添付ファイル",
    description: "Item in delete account list",
  },
  "userSettings.allLedgersAndTransactions": {
    message: "すべての元帳と取引履歴",
    description: "Item in delete account list",
  },
  "userSettings.allPreferencesAndSettings": {
    message: "すべての設定と環境設定",
    description: "Item in delete account list",
  },
  "userSettings.allTransactionsAndRecords": {
    message: "すべての取引と記録",
    description: "Item in delete account list",
  },
  "userSettings.appearance": {
    message: "外観",
    description: "Appearance settings section label",
  },
  "userSettings.cannotBeUndone": {
    message: "この操作は元に戻せません。",
    description: "Warning that action is irreversible",
  },
  "userSettings.changeUsername": {
    message: "ユーザー名を変更",
    description: "Dialog title for changing username",
  },
  "userSettings.createKey": {
    message: "キーを作成",
    description: "Button text to create key",
  },
  "userSettings.createNewApiKey": {
    message: "新しい SSH キーを作成",
    description: "Dialog title for creating an SSH public key",
  },
  "userSettings.createNewApiKeyDescription": {
    message: "Git リポジトリへのアクセス用に新しい SSH 公開鍵を追加します。",
    description:
      "Dialog description for creating an SSH public key for Git access",
  },
  "userSettings.createNewKey": {
    message: "新しいキーを作成",
    description: "Button text to create new key",
  },
  "userSettings.creating": {
    message: "作成中...",
    description: "Button text while creating key",
  },
  "userSettings.currentLanguage": {
    message: "言語",
    description: "Label showing current language selection",
  },
  "userSettings.customizeAppearance": {
    message: "アプリケーションの外観をカスタマイズ",
    description: "Description for appearance settings",
  },
  "userSettings.dangerZone": {
    message: "危険ゾーン",
    description: "Section title for dangerous account actions",
  },
  "userSettings.dark": {
    message: "ダーク",
    description: "Dark theme option",
  },
  "userSettings.deleteAccount": {
    message: "アカウントを削除",
    description: "Button or menu item to delete user account",
  },
  "userSettings.deleteAccountConfirmMessage": {
    message: "確認のため、下にユーザー名「{username}」を入力してください：",
    description:
      "Instructions for confirming account deletion by typing username",
  },
  "userSettings.deleteAccountConfirmPlaceholder": {
    message: "ユーザー名を入力",
    description: "Placeholder text for deletion confirmation input",
  },
  "userSettings.deleteAccountDialogDescription": {
    message:
      "この操作は元に戻せません。アカウントが完全に削除され、すべてのデータがサーバーから削除されます。",
    description: "Detailed warning in delete account dialog",
  },
  "userSettings.deleteAccountQuestion": {
    message: "アカウントを削除しますか？",
    description: "Dialog title confirming account deletion",
  },
  "userSettings.deleteAccountWarning": {
    message:
      "アカウントとすべての関連データを完全に削除します。この操作は元に戻せません。",
    description: "Warning text for account deletion",
  },
  "userSettings.deleteKey": {
    message: "キーを削除",
    description: "Button text to delete key",
  },
  "userSettings.deleteSshKey": {
    message: "SSHキーを削除",
    description: "Dialog title for deleting SSH key",
  },
  "userSettings.deleteSshKeyConfirmation": {
    message: "このキーを削除してよろしいですか",
    description: "Confirmation message for deleting SSH key",
  },
  "userSettings.deletingKey": {
    message: "削除中...",
    description: "Button text while deleting key",
  },
  "userSettings.enterNewUsername": {
    message: "下に新しいユーザー名を入力してください",
    description: "Instructions in change username dialog",
  },
  "userSettings.enterNewUsernamePlaceholder": {
    message: "新しいユーザー名を入力",
    description: "Placeholder for new username input",
  },
  "userSettings.errorCreatingKey": {
    message: "キーの作成エラー",
    description: "Error title when key creation fails",
  },
  "userSettings.errorLoadingSettings": {
    message: "設定の読み込みエラー",
    description: "Error message when settings fail to load",
  },
  "userSettings.failedToLoadKeys": {
    message: "キーの読み込みに失敗しました",
    description: "Error title when keys fail to load",
  },
  "userSettings.failedToLoadKeysDescription": {
    message:
      "SSHキーの読み込み中にエラーが発生しました。もう一度お試しください。",
    description: "Error description when keys fail to load",
  },
  "userSettings.failedToLoadSettings": {
    message: "設定の読み込みに失敗しました",
    description: "Error heading when settings page fails",
  },
  "userSettings.failedToLoadSubscription": {
    message: "サブスクリプションの状態の読み込みに失敗しました",
    description: "Error message when subscription fails to load",
  },
  "userSettings.followingWillBeDeleted": {
    message: "以下のデータが完全に削除されます：",
    description: "Heading before list of items to be deleted",
  },
  "userSettings.general": {
    message: "一般",
    description: "General settings section label",
  },
  "userSettings.invite": {
    message: "招待",
    description: "Invite action button",
  },
  "userSettings.irreversibleActions": {
    message: "元に戻せない破壊的な操作",
    description: "Description for danger zone",
  },
  "userSettings.keyTitle": {
    message: "キーのタイトル",
    description: "Label for key title field",
  },
  "userSettings.keyTitleDescription": {
    message: "後で識別しやすいように、このキーの説明的な名前を付けてください。",
    description: "Description for key title field",
  },
  "userSettings.keyTitlePlaceholder": {
    message: "例：開発用キー",
    description: "Placeholder for key title input",
  },
  "userSettings.lastUsed3Months": {
    message: "直近3か月以内に使用",
    description: "Status when key was used within last 3 months",
  },
  "userSettings.lastUsed3Weeks": {
    message: "直近3週間以内に使用",
    description: "Status when key was used within last 3 weeks",
  },
  "userSettings.lastUsedLongAgo": {
    message: "3か月以上前に使用",
    description: "Status when key was used long ago",
  },
  "userSettings.lastUsedWeek": {
    message: "直近1週間以内に使用",
    description: "Status when key was used within last week",
  },
  "userSettings.light": {
    message: "ライト",
    description: "Light theme option",
  },
  "userSettings.loadingAccountInformation": {
    message: "アカウント情報を読み込み中...",
    description: "Loading message for account information",
  },
  "userSettings.loadingSessionInformation": {
    message: "セッション情報を読み込み中...",
    description: "Loading message for session data",
  },
  "userSettings.loadingSshKeys": {
    message: "SSHキーを読み込み中...",
    description: "Loading state message for SSH keys",
  },
  "userSettings.loadingSubscriptionDetails": {
    message: "サブスクリプションの詳細を読み込み中...",
    description: "Loading message for subscription info",
  },
  "userSettings.loadingThemePreferences": {
    message: "テーマ設定を読み込み中...",
    description: "Loading message for theme settings",
  },
  "userSettings.cancelSubscription": {
    message: "サブスクリプションをキャンセル",
    description: "Button text to cancel subscription",
  },
  "userSettings.cancelSubscriptionDescription": {
    message:
      "サブスクリプションをキャンセルしてよろしいですか？現在の請求期間が終了するまでアクセスを継続できます。",
    description: "Confirmation dialog description for canceling subscription",
  },
  "userSettings.cancelSubscriptionTitle": {
    message: "サブスクリプションをキャンセルしますか？",
    description: "Confirmation dialog title for canceling subscription",
  },
  "userSettings.canceling": {
    message: "キャンセル中...",
    description: "Button text while canceling subscription",
  },
  "userSettings.confirmCancel": {
    message: "はい、キャンセルする",
    description: "Button text to confirm subscription cancellation",
  },
  "userSettings.failedToCancelSubscription": {
    message: "サブスクリプションのキャンセルに失敗しました",
    description: "Error message when canceling subscription fails",
  },
  "userSettings.resumeSubscription": {
    message: "サブスクリプションを再開",
    description: "Button text to resume a subscription scheduled to cancel",
  },
  "userSettings.resumeSubscriptionTitle": {
    message: "サブスクリプションを再開しますか？",
    description: "Confirmation dialog title for resuming subscription",
  },
  "userSettings.resumeSubscriptionDescription": {
    message:
      "サブスクリプションを再開してもよろしいですか？サブスクリプションは引き続き自動更新され、現在の請求期間の終了時に再度請求されます。",
    description: "Confirmation dialog description for resuming subscription",
  },
  "userSettings.confirmResume": {
    message: "はい、サブスクリプションを再開します",
    description: "Button text to confirm subscription resumption",
  },
  "userSettings.resuming": {
    message: "再開中...",
    description: "Button text while resuming subscription",
  },
  "userSettings.subscriptionResumedSuccess": {
    message: "サブスクリプションが正常に再開されました",
    description: "Success message after resuming subscription",
  },
  "userSettings.failedToResumeSubscription": {
    message: "サブスクリプションの再開に失敗しました",
    description: "Error message when resuming subscription fails",
  },
  "userSettings.failedToCreateCheckoutSession": {
    message:
      "チェックアウトセッションの作成に失敗しました。もう一度お試しください。",
    description: "Error message when creating checkout session fails",
  },
  "userSettings.manageBilling": {
    message: "請求を管理",
    description: "Button text to manage billing portal",
  },
  "userSettings.manageActiveSession": {
    message: "アクティブなセッションを管理",
    description: "Description for session section",
  },
  "userSettings.manageSubscription": {
    message: "サブスクリプションと請求を管理",
    description: "Description for subscription section",
  },
  "userSettings.monthly": {
    message: "毎月",
    description: "Monthly frequency option",
  },
  "userSettings.neverUsed": {
    message: "未使用",
    description: "Status when key has never been used",
  },
  "userSettings.newSshKey": {
    message: "新しいSSHキー",
    description: "Button text to create new SSH key",
  },
  "userSettings.noSshKeys": {
    message: "SSHキーなし",
    description: "Empty state title when no SSH keys exist",
  },
  "userSettings.noSshKeysDescription": {
    message:
      "まだSSHキーが作成されていません。最初のキーを作成して、安全なリポジトリアクセスを始めましょう。",
    description: "Empty state description for SSH keys",
  },
  "userSettings.notSet": {
    message: "未設定",
    description: "Placeholder when a field has no value",
  },
  "userSettings.opening": {
    message: "開いています...",
    description: "Button text while opening billing portal",
  },
  "userSettings.publicKey": {
    message: "公開鍵",
    description: "Label for public key field",
  },
  "userSettings.publicKeyDescription": {
    message:
      "公開鍵をここに貼り付けてください。通常は ssh-ed25519 または ssh-rsa で始まり、cat ~/.ssh/id_ed25519.pub で表示できます。PEM 形式の公開鍵も使用できます。",
    description: "Description for public key field",
  },
  "userSettings.publicKeyPlaceholder": {
    message: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA…",
    description: "Placeholder for public key textarea",
  },
  "userSettings.publicKeyRequired": {
    message: "公開鍵は必須です",
    description: "Validation error for missing public key",
  },
  "userSettings.renewsOn": {
    message: "更新日",
    description: "Label for subscription renewal date",
  },
  "userSettings.selectColorTheme": {
    message: "お好みのカラーテーマを選択",
    description: "Label for theme selection",
  },
  "userSettings.selectLanguage": {
    message: "お好みの言語を選択",
    description: "Label for language selection",
  },
  "userSettings.session": {
    message: "セッション",
    description: "Session management section title",
  },
  "userSettings.signOutDescription": {
    message: "アカウントからサインアウトし、セッションをクリアします。",
    description: "Description for logout action",
  },
  "userSettings.sshKeys": {
    message: "SSHキー",
    description: "Page title for SSH keys",
  },
  "userSettings.subscription": {
    message: "サブスクリプション",
    description: "Subscription section title",
  },
  "userSettings.subscriptionCanceled": {
    message: "サブスクリプションがキャンセルされました",
    description: "Message when subscription is already canceled",
  },
  "userSettings.subscriptionCanceledSuccess": {
    message: "サブスクリプションが正常にキャンセルされました",
    description: "Success message after canceling subscription",
  },
  "userSettings.subscriptionUpgraded": {
    message: "サブスクリプションが正常にアップグレードされました",
    description: "Success message after upgrading subscription",
  },
  "userSettings.paymentRequiresAuth": {
    message:
      "お支払いには追加認証が必要です。メールまたはカード発行会社をご確認ください。",
    description:
      "Message when 3DS authentication is needed for subscription upgrade",
  },
  "userSettings.system": {
    message: "システム",
    description: "System theme option",
  },
  "userSettings.theme": {
    message: "テーマ",
    description: "Label for theme selection",
  },
  "userSettings.themeDark": {
    message: "ダーク",
    description: "Dark theme option",
  },
  "userSettings.themeLight": {
    message: "ライト",
    description: "Light theme option",
  },
  "userSettings.themeSystem": {
    message: "システム",
    description: "System theme option (follows OS preference)",
  },
  "userSettings.titleMaxLength": {
    message: "タイトルは100文字未満にしてください",
    description: "Validation error for title too long",
  },
  "userSettings.titleRequired": {
    message: "タイトルは必須です",
    description: "Validation error for missing title",
  },
  "userSettings.unableToOpenBillingPortal": {
    message: "請求ポータルを開けません。後でもう一度お試しください。",
    description: "Error message when billing portal fails to open",
  },
  "userSettings.unknownPlan": {
    message: "不明なプラン",
    description: "Fallback when plan name is not available",
  },
  "userSettings.usernameUpdatedSuccess": {
    message: "ユーザー名が正常に更新されました",
    description: "Success message after updating username",
  },
  "userSettings.userProfile": {
    message: "ユーザープロフィール",
    description: "Section title for user profile settings",
  },
  "userSettings.weekly": {
    message: "毎週",
    description: "Weekly frequency option",
  },
  "userSettings.yesDeleteMyAccount": {
    message: "はい、アカウントを削除します",
    description: "Confirmation button for account deletion",
  },
  "userSettings.yourAccountInformation": {
    message: "あなたのアカウント情報",
    description: "Description for user profile section",
  },
  "userSettings.firstName": {
    message: "名",
    description: "Label for first name field",
  },
  "userSettings.lastName": {
    message: "姓",
    description: "Label for last name field",
  },
  "userSettings.name": {
    message: "氏名",
    description: "Label for combined name field",
  },
  "userSettings.changeName": {
    message: "名前を変更",
    description: "Dialog title for changing name",
  },
  "userSettings.enterNewName": {
    message: "下に名前を入力してください",
    description: "Instructions in change name dialog",
  },
  "userSettings.aiCfoUsage": {
    message: "AIリクエスト",
    description: "Label for AI CFO usage section",
  },
  "userSettings.aiCfoUsageCount": {
    message: "今月 {used} / {max} リクエスト使用済み",
    description: "AI CFO usage count display",
  },
  "userSettings.aiCfoUsageUnlimited": {
    message: "今月 {used} リクエスト使用済み（無制限）",
    description: "AI CFO usage display for unlimited tier",
  },
  "userSettings.currentPlan": {
    message: "現在のプラン",
    description: "Badge label for the user's current subscription tier",
  },
  "userSettings.freePlan": {
    message: "無料プラン",
    description: "Display name for the free tier",
  },
  "userSettings.enterprisePlan": {
    message: "エンタープライズ",
    description: "Display name for the enterprise tier",
  },
  "userSettings.usage": {
    message: "使用状況",
    description: "Section header for usage overview",
  },
  "userSettings.ledgers": {
    message: "元帳",
    description: "Label for ledger usage metric",
  },
  "userSettings.ledgerUsageCount": {
    message: "{used} / {max} 元帳",
    description: "Ledger usage count display",
  },
  "userSettings.billing": {
    message: "請求",
    description: "Section header for billing management",
  },
  "userSettings.unlimited": {
    message: "無制限",
    description: "Label for unlimited usage",
  },
  "userSettings.perMonth": {
    message: "/月",
    description: "Price interval suffix",
  },
  "userSettings.aiTokensPerMonth": {
    message: "{count} AI トークン / 月",
    description: "AI token allowance for a subscription tier",
  },
  "userSettings.unlimitedLedgers": {
    message: "無制限の台帳",
    description: "Unlimited ledger allowance",
  },
  "userSettings.includedLedgers": {
    message: "元帳 {formattedCount} 件",
    description:
      "Ledger allowance for a subscription tier - interpolation: {formattedCount} is the count formatted in the app language; {count} selects the plural form (base key for pluralization)",
  },
  "userSettings.includedLedgers_other": {
    message: "元帳 {formattedCount} 件",
    description:
      "Ledger allowance for a subscription tier - interpolation: {formattedCount} is the count formatted in the app language; {count} selects the plural form - the only form; this language has no plural inflection",
  },
  "userSettings.unlimitedDirectives": {
    message: "無制限のディレクティブ",
    description: "Unlimited directive allowance",
  },
  "userSettings.includedDirectives": {
    message: "{count} ディレクティブ",
    description: "Directive allowance for a subscription tier",
  },
  "userSettings.unlimitedCollaborators": {
    message: "無制限のコラボレーター",
    description: "Unlimited collaborator allowance",
  },
  "userSettings.collaboratorsPerLedger": {
    message: "元帳ごとに最大 {formattedCount} 人の共同作業者",
    description:
      "Collaborator allowance for each ledger - interpolation: {formattedCount} is the count formatted in the app language; {count} selects the plural form (base key for pluralization)",
  },
  "userSettings.collaboratorsPerLedger_other": {
    message: "元帳ごとに最大 {formattedCount} 人の共同作業者",
    description:
      "Collaborator allowance for each ledger - interpolation: {formattedCount} is the count formatted in the app language; {count} selects the plural form - the only form; this language has no plural inflection",
  },
  "userSettings.aiUsageUpgradeNudge": {
    message:
      "毎月の AI トークンの {percentage}% を使用しています。中断を避けるためにアップグレードしてください。",
    description: "Upgrade suggestion when AI token usage is high",
  },
  "userSettings.fingerprint": {
    message: "指紋",
    description: "Label for an SSH key fingerprint",
  },
  "userSettings.yearly": {
    message: "毎年",
    description: "Yearly billing option in the billing-cycle toggle",
  },
  "userSettings.billingCycle": {
    message: "請求サイクル",
    description: "Accessible label for the monthly/yearly billing-cycle toggle",
  },
  "userSettings.plans": {
    message: "プラン",
    description: "Section header above every plan on the Billing page",
  },
  "userSettings.switchToYearly": {
    message: "年払いに切り替える",
    description: "Button that moves a monthly subscription to yearly billing",
  },
  "userSettings.switchToMonthly": {
    message: "月払いに切り替える",
    description: "Button that moves a yearly subscription to monthly billing",
  },
  "userSettings.downgrade": {
    message: "ダウングレード",
    description: "Button for moving to a lower plan",
  },
  "userSettings.contactUs": {
    message: "お問い合わせ",
    description: "Enterprise plan call to action and price label",
  },
  "userSettings.renewalChangesComingSoon": {
    message: "更新日から適用される変更には近日対応予定です。",
    description:
      "Hint under a plan change that takes effect at renewal, which is not available yet",
  },
  "userSettings.billedYearly": {
    message: "年額 {amount}",
    description: "Total charged once a year; {amount} is a formatted price",
  },
  "userSettings.saveYearlyPercent": {
    message: "{percent}%お得",
    description: "Badge with the yearly saving; {percent} is a whole number",
  },
  "userSettings.payYearlyOffer": {
    message:
      "年払いなら年額 {yearly}（月払いでは {monthlyTotal}）で、毎年 {saving} お得です。",
    description:
      "Offer on a monthly plan; {yearly}, {monthlyTotal} and {saving} are formatted prices",
  },
  "userSettings.perYear": {
    message: "/年",
    description: "Price interval suffix for yearly prices",
  },
  "userSettings.legacyPrice": {
    message: "旧料金",
    description: "Label for an older price an existing subscriber keeps",
  },
  "userSettings.checkoutConfirming": {
    message: "お支払いを確認しています…",
    description:
      "Shown while waiting for Stripe to confirm a just-completed checkout",
  },
  "userSettings.checkoutDone": {
    message: "{plan} をご利用中です",
    description:
      "Confirmation after checkout; {plan} is a plan name and billing cycle such as 'Premium \u00b7 Yearly'",
  },
  "userSettings.checkoutRenews": {
    message: "{date} に {amount} で更新されます。領収書はメールで届きます。",
    description:
      "Renewal line after checkout; {date} is a formatted date and {amount} a formatted price",
  },
  "userSettings.checkoutUnlocked": {
    message: "利用できるようになった内容: {limits}",
    description: "What the new plan includes; {limits} is a list of quotas",
  },
  "userSettings.checkoutPending": {
    message:
      "お支払いを受け付けました。1 分ほどでプランが反映されます。更新して確認してください。",
    description:
      "Shown when the payment is done but the subscription is not recorded yet",
  },
  "userSettings.refresh": {
    message: "更新",
    description: "Button that reloads the subscription status",
  },
  "userSettings.backToWork": {
    message: "元のページに戻る",
    description: "Button that returns to the page where the purchase began",
  },
  "userSettings.viewBilling": {
    message: "お支払い情報を見る",
    description:
      "Button that closes the checkout confirmation and shows billing settings",
  },
};

export default jaUserSettings;
