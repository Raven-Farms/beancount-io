import fs from "fs";
import path from "path";
import {
  BUDGET_ROW_HEIGHT,
  BUDGET_ROWS,
  budgetSkeletonHeight,
  ENTRY_ROW_HEIGHT,
  FEED_ROW_HEIGHT,
  FEED_ROW_WRAPPED_HEIGHT,
  FEED_ROWS,
  feedSkeletonHeight,
  RECENT_ROWS,
  recentSkeletonHeight,
} from "../home-skeleton-heights";

// w21/264: Home's lower cards loaded with one short tile each, so everything
// below jumped by 160 to 260 pt when the data arrived.
const read = (...parts: string[]) =>
  fs.readFileSync(path.join(__dirname, "..", ...parts), "utf8");
const readSrc = (...parts: string[]) =>
  fs.readFileSync(
    path.join(__dirname, "..", "..", "..", "..", ...parts),
    "utf8",
  );

describe("Home skeleton heights", () => {
  it("match the loaded rows each card draws", () => {
    // Recent Transactions: the entry row is a 40 pt icon with 12 pt above and
    // below.
    expect(ENTRY_ROW_HEIGHT).toBe(64);
    expect(recentSkeletonHeight(RECENT_ROWS)).toBe(320);
    const list = readSrc(
      "screens",
      "transactions-screen",
      "transactions-list-skeleton.tsx",
    );
    expect(/paddingVertical: 12/.test(list) && /height: 40/.test(list)).toBe(
      true,
    );

    // Latest Updates: 8 + 18 + 2 + 15 + 8, and 18 more when the title wraps.
    const feed = read("feed-card.tsx");
    expect(/paddingVertical: 8/.test(feed)).toBe(true);
    expect(/lineHeight: 18/.test(feed)).toBe(true);
    expect(/marginTop: 2/.test(feed)).toBe(true);
    expect(FEED_ROW_HEIGHT).toBe(8 + 18 + 2 + 15 + 8);
    expect(FEED_ROW_WRAPPED_HEIGHT).toBe(FEED_ROW_HEIGHT + 18);
    // Five rows: between all one-line (255) and all wrapped (345).
    const total = feedSkeletonHeight(FEED_ROWS);
    expect(
      total >= 5 * FEED_ROW_HEIGHT && total <= 5 * FEED_ROW_WRAPPED_HEIGHT,
    ).toBe(true);

    // Budget: a 17 pt header, a 4 pt gap and the 6 pt meter, 12 pt between
    // rows.
    expect(BUDGET_ROW_HEIGHT).toBe(27);
    expect(budgetSkeletonHeight(BUDGET_ROWS)).toBe(3 * 27 + 2 * 12);
    expect(
      /height=\{6\}/.test(
        readSrc("screens", "budget-screen", "components", "budget-meter.tsx"),
      ),
    ).toBe(true);
  });

  it("draw as many rows as the cards show", () => {
    expect(
      /const RECENT_LIMIT = 5;/.test(read("recent-transactions-card.tsx")),
    ).toBe(true);
    expect(/const FEED_LIMIT = 5;/.test(read("feed-card.tsx"))).toBe(true);
    expect(
      /const BUDGET_PANEL_ROWS = 3;/.test(
        readSrc("screens", "home-screen", "hooks", "use-budget-panel.ts"),
      ),
    ).toBe(true);
    expect([RECENT_ROWS, FEED_ROWS, BUDGET_ROWS]).toEqual([5, 5, 3]);
  });

  it("are what the three cards show while loading", () => {
    expect(
      read("recent-transactions-card.tsx").includes(
        "<RecentTransactionsSkeleton />",
      ),
    ).toBe(true);
    expect(read("feed-card.tsx").includes("<FeedSkeleton />")).toBe(true);
    expect(read("budget-card.tsx").includes("<BudgetSkeleton />")).toBe(true);
    expect(
      read("recent-transactions-card.tsx").includes("LoadingTile height={160}"),
    ).toBe(false);
  });
});
