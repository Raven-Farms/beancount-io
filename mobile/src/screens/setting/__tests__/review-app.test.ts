import fs from "fs";
import path from "path";
import { openReviewPage, reviewUrls } from "../review-app";

// w21/404: the row opened the web listing in an in-app browser, which has no
// write-review action (and errored on the simulator).
describe("the review row", () => {
  it("goes to the store apps' write-review links, with no storefront", () => {
    const ios = reviewUrls("ios");
    expect(ios.app).toEqual([
      "itms-apps://apps.apple.com/app/id1527950512?action=write-review",
    ]);
    expect(ios.web.includes("/us/")).toBe(false);
    expect(reviewUrls("android").app).toEqual([
      "market://details?id=io.beancount.android",
    ]);
  });

  it("opens the store app when the device will, and nothing else", async () => {
    const opened: string[] = [];
    await openReviewPage(
      "ios",
      async (url) => void opened.push(url),
      async (url) => void opened.push(`web:${url}`),
    );
    expect(opened).toEqual([reviewUrls("ios").app[0]]);
  });

  it("falls back to the https listing when the store link will not open", async () => {
    const opened: string[] = [];
    await openReviewPage(
      "android",
      async () => {
        throw new Error("no handler");
      },
      async (url) => void opened.push(url),
    );
    expect(opened).toEqual([reviewUrls("android").web]);
  });

  it("is what Settings does, in place of the in-app browser on the listing", () => {
    const src = fs
      .readFileSync(path.join(__dirname, "..", "main-content.tsx"), "utf8")
      .replace(/\s+/g, "");
    expect(src.includes("voidopenReviewPage(Platform.OS,")).toBe(true);
    expect(src.includes("apps.apple.com")).toBe(false);
    expect(src.includes("play.google.com")).toBe(false);
  });
});
