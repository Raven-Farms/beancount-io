/**
 * Where "Like it? Give it a review" goes. The web listings have no write-review
 * action, and an in-app browser does not hand off to the store app, so the row
 * opened a page that could not take a review (and, on the simulator, an
 * "address is invalid" error from the redirect to the App Store scheme)
 * (w21/404). The store apps' own write-review links come first, the https
 * listing last.
 *
 * Free of `@/` imports so the jest-lite runner can require it.
 */
const IOS_APP_ID = "id1527950512";
const ANDROID_PACKAGE = "io.beancount.android";

export function reviewUrls(os: string): { app: string[]; web: string } {
  return os === "ios"
    ? {
        // No storefront in the path: the `/us/` listing sent every other
        // country to the US store.
        app: [
          `itms-apps://apps.apple.com/app/${IOS_APP_ID}?action=write-review`,
        ],
        web: `https://apps.apple.com/app/${IOS_APP_ID}?action=write-review`,
      }
    : {
        app: [`market://details?id=${ANDROID_PACKAGE}`],
        web: `https://play.google.com/store/apps/details?id=${ANDROID_PACKAGE}`,
      };
}

/**
 * Open the store's review page: the store app if the device will open its link,
 * else the https listing in the browser. `openApp` rejects when nothing handles
 * the URL.
 */
export async function openReviewPage(
  os: string,
  openApp: (url: string) => Promise<unknown>,
  openWeb: (url: string) => Promise<unknown>,
): Promise<void> {
  const { app, web } = reviewUrls(os);
  for (const url of app) {
    try {
      await openApp(url);
      return;
    } catch {
      // Not opened here (a simulator without the store, a device without
      // Google Play): try the next way.
    }
  }
  await openWeb(web);
}
