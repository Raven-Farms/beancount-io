const SITE = "https://beancount.io";

/**
 * A beancount.io page in the app's language. The site serves each translated
 * page under a bare language prefix (`/de/docs/help-center`) and the
 * unprefixed URL stays English whatever the browser asks for, so the prefix
 * is built here (w21/286). English has none.
 */
function localizedSiteUrl(path: string, locale: string): string {
  return /^[a-z]{2}$/.test(locale) && locale !== "en"
    ? `${SITE}/${locale}${path}`
    : `${SITE}${path}`;
}

export const helpCenterUrl = (locale: string): string =>
  localizedSiteUrl("/docs/help-center", locale);
