import { FeedSource } from "../../../../generated-graphql/types";
import fs from "fs";
import path from "path";
import { feedQueryVariables, feedSourceLabelKey } from "../feed-logic";

describe("feedSourceLabelKey", () => {
  it("labels every source, with releases no longer read as blog posts", () => {
    expect(feedSourceLabelKey(FeedSource.LedgerRss)).toBe("feedSourceLedger");
    expect(feedSourceLabelKey(FeedSource.Blog)).toBe("feedSourceBlog");
    expect(feedSourceLabelKey(FeedSource.Changelog)).toBe("feedSourceRelease");
  });
});

// w21/136: the card asked for the English feed whatever the app language.
describe("feedQueryVariables", () => {
  it("asks for the feed in the app's language", () => {
    expect(feedQueryVariables(5, "de")).toEqual({
      offset: 0,
      limit: 5,
      locale: "de",
    });
  });

  it("is what the card queries with, from the live locale", () => {
    const card = fs.readFileSync(
      path.join(__dirname, "..", "feed-card.tsx"),
      "utf8",
    );
    expect(card.includes("const { t, locale } = useTranslations();")).toBe(
      true,
    );
    expect(
      card.includes("variables: feedQueryVariables(FEED_LIMIT, locale),"),
    ).toBe(true);
    expect(card.includes('locale: "en"')).toBe(false);
  });
});
