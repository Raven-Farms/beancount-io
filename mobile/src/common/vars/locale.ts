import { createPersistentVar } from "@/common/apollo/persistent-var";
import { i18n } from "@/translations";

/**
 * The app's language. Until the user picks one in Settings it follows the
 * device (`i18n.locale`, the first supported device language): defaulting to
 * "en" made the first `useTranslations` switch a German device to English and
 * left a Persian one in English text on an RTL layout (w21/126). A default is
 * never written to storage, so the device keeps deciding until a choice.
 */
export const [localeVar, loadLocale, flushLocale] = createPersistentVar<string>(
  "locale",
  i18n.locale,
);
