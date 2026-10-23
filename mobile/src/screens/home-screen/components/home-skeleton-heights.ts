import { space } from "../../../common/theme/spacing";

/**
 * Row heights for Home's lower-card skeletons, kept free of React Native so a
 * test can load them. A single short tile under each card made everything below
 * it jump by 160 to 260 pt when the data arrived (w21/264); these are the
 * loaded rows' own heights and counts.
 */

/** An entry row: its 40 pt icon plus 12 pt of padding above and below. */
export const ENTRY_ROW_HEIGHT = 40 + 12 * 2;
/** A feed row with a one-line title: 8 + 18 + 2 + 15 + 8. */
export const FEED_ROW_HEIGHT = 51;
/** A feed row whose title wraps to a second 18 pt line. */
export const FEED_ROW_WRAPPED_HEIGHT = FEED_ROW_HEIGHT + 18;
/** A budget row: its 17 pt header, 4 pt gap and 6 pt meter. */
export const BUDGET_ROW_HEIGHT = 17 + space.xs + 6;

/** Rows the three cards show once loaded. */
export const RECENT_ROWS = 5;
export const FEED_ROWS = 5;
export const BUDGET_ROWS = 3;

/** Total skeleton heights, pinned against the loaded rows by tests. */
export const recentSkeletonHeight = (rows: number): number =>
  rows * ENTRY_ROW_HEIGHT;
export const feedSkeletonHeight = (rows: number): number =>
  Array.from({ length: rows }, (_, index) =>
    index % 2 === 0 ? FEED_ROW_HEIGHT : FEED_ROW_WRAPPED_HEIGHT,
  ).reduce((sum, height) => sum + height, 0);
export const budgetSkeletonHeight = (rows: number): number =>
  rows * BUDGET_ROW_HEIGHT + Math.max(0, rows - 1) * space.md;
