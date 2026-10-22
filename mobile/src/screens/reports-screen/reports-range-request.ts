import { makeVar } from "@apollo/client";
import type { TimeRange } from "../../common/series-util";

/**
 * A range another screen wants Reports to open on. Reports is a tab that stays
 * mounted, so a route parameter would not reach it twice with the same value;
 * this is read once and cleared. Home's Spending "See all" asks for 1M, the
 * month its "This month" figure covers: Reports opened on its own 6M and showed
 * totals that matched neither figure (w21/611).
 */
export const requestedReportsRange = makeVar<TimeRange | null>(null);
