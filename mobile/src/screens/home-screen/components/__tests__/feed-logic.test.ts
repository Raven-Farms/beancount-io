import { FeedSource } from "../../../../generated-graphql/types";
import fs from "fs";
import path from "path";
import {
  feedDateIsCalendarDay,
  feedQueryVariables,
  feedRowAction,
  feedSourceLabelKey,
} from "../feed-logic";

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

// w21/137: ledger activity rows carry relative links the row ignored.
describe("feedRowAction", () => {
  const server = "https://beancount.io/";

  it("opens a commit row's commit in the app", () => {
    const action = feedRowAction("/ledger/alice/books/commit/abc123", server);
    expect(JSON.stringify(action)).toBe(
      JSON.stringify({
        kind: "ledger",
        target: {
          ledgerFullName: "alice/books",
          href: {
            pathname: "/commit-detail",
            params: { sha: "abc123", ledger: "alice/books" },
          },
        },
        sourceUrl: "https://beancount.io/ledger/alice/books/commit/abc123",
      }),
    );
  });

  it("opens a ledger-level row's ledger", () => {
    const action = feedRowAction("/ledger/alice/books", server);
    expect(action?.kind === "ledger" && action.target.href).toBe("/");
  });

  it("links out for blog and release rows", () => {
    expect(feedRowAction("https://beancount.io/blog/post", server)).toEqual({
      kind: "external",
      url: "https://beancount.io/blog/post",
    });
  });

  it("is no action for a link that resolves to nothing", () => {
    expect(feedRowAction("/settings", server)).toBe(null);
    expect(feedRowAction("", server)).toBe(null);
  });
});

describe("the feed row", () => {
  it("acts on feedRowAction, opening ledger links in the app with a push", () => {
    const card = fs.readFileSync(
      path.join(__dirname, "..", "feed-card.tsx"),
      "utf8",
    );
    expect(card.includes("feedRowAction(link, getServerUrl())")).toBe(true);
    expect(card.includes('navigation: "push"')).toBe(true);
    expect(card.includes("disabled={!action}")).toBe(true);
  });
});

describe("feedDateIsCalendarDay", () => {
  it("reads blog and release dates as days, ledger activity as instants", () => {
    expect(feedDateIsCalendarDay(FeedSource.Blog)).toBe(true);
    expect(feedDateIsCalendarDay(FeedSource.Changelog)).toBe(true);
    expect(feedDateIsCalendarDay(FeedSource.LedgerRss)).toBe(false);
  });

  it("is what the row formats its date with", () => {
    const card = fs.readFileSync(
      path.join(__dirname, "..", "feed-card.tsx"),
      "utf8",
    );
    expect(card.includes("calendarDay: feedDateIsCalendarDay(source),")).toBe(
      true,
    );
  });
});

// w21/417: an empty feed (any RSS outage) drew a "Latest Updates" header over a
// blank card.
describe("feedCardIsEmpty", () => {
  const { feedCardIsEmpty } = require("../feed-logic");

  it("hides the card when the feed came back empty", () => {
    expect(
      feedCardIsEmpty({ failed: false, loading: false, itemCount: 0 }),
    ).toBe(true);
  });

  it("keeps it for updates, a load in flight and a failure", () => {
    expect(
      feedCardIsEmpty({ failed: false, loading: false, itemCount: 3 }),
    ).toBe(false);
    expect(
      feedCardIsEmpty({ failed: false, loading: true, itemCount: 0 }),
    ).toBe(false);
    expect(
      feedCardIsEmpty({ failed: true, loading: false, itemCount: 0 }),
    ).toBe(false);
  });

  it("is what the card renders, ahead of its header", () => {
    const src = require("fs")
      .readFileSync(
        require("path").join(__dirname, "..", "feed-card.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "");
    const hidden = src.indexOf("returnnull;");
    expect(
      hidden > -1 && hidden < src.indexOf('title={t("latestUpdates")}'),
    ).toBe(true);
    expect(src.includes('feedCardIsEmpty({failed:loadState==="failed",')).toBe(
      true,
    );
  });
});
