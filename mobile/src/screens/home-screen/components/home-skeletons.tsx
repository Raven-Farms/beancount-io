import { StyleSheet, View } from "react-native";
import { space } from "@/common/theme";
import {
  BUDGET_ROWS,
  budgetSkeletonHeight,
  ENTRY_ROW_HEIGHT,
  FEED_ROWS,
  feedSkeletonHeight,
  RECENT_ROWS,
  recentSkeletonHeight,
} from "./home-skeleton-heights";
import { LoadingTile } from "@/components/loading-tile";

/**
 * Skeletons for Home's lower cards, built row by row at the loaded rows' own
 * heights and count. A single short tile under each card made everything below
 * it jump by 160 to 260 pt when the data arrived, against the rule that the
 * view must not shift when data lands (w21/264).
 */

const styles = StyleSheet.create({
  entryRow: {
    flexDirection: "row",
    alignItems: "center",
    height: ENTRY_ROW_HEIGHT,
    paddingHorizontal: 16,
  },
  icon: { width: 40, height: 40, borderRadius: 12, marginEnd: 12 },
  name: { flex: 1 },
  amount: { height: 14, width: 68, marginStart: 8 },
  feedRow: { paddingHorizontal: 16, paddingVertical: 8 },
  budgetRow: { marginBottom: space.md },
  budgetRowLast: { marginBottom: 0 },
});

const NAME_WIDTHS = ["62%", "78%", "45%", "70%", "55%"] as const;

/** Recent Transactions: the loaded rows' icon, name and amount, five times. */
export function RecentTransactionsSkeleton(): JSX.Element {
  return (
    <View
      testID="recent-transactions-skeleton"
      style={{ height: recentSkeletonHeight(RECENT_ROWS) }}
    >
      {Array.from({ length: RECENT_ROWS }, (_, index) => (
        <View key={index} style={styles.entryRow}>
          <LoadingTile style={styles.icon} />
          <View style={styles.name}>
            <LoadingTile height={16} style={{ width: NAME_WIDTHS[index] }} />
          </View>
          <LoadingTile style={styles.amount} />
        </View>
      ))}
    </View>
  );
}

/** Latest Updates: a title line (every other row wraps) and a source line. */
export function FeedSkeleton(): JSX.Element {
  return (
    <View
      testID="feed-skeleton"
      style={{ height: feedSkeletonHeight(FEED_ROWS) }}
    >
      {Array.from({ length: FEED_ROWS }, (_, index) => (
        <View key={index} style={styles.feedRow}>
          <LoadingTile height={18} style={{ width: "90%" }} />
          {index % 2 === 1 ? (
            <LoadingTile height={18} style={{ width: "60%" }} />
          ) : null}
          <LoadingTile height={15} style={{ width: "40%", marginTop: 2 }} />
        </View>
      ))}
    </View>
  );
}

/** Budget: a header line over a meter, three times, with the loaded gaps. */
export function BudgetSkeleton(): JSX.Element {
  return (
    <View
      testID="budget-skeleton"
      style={{ height: budgetSkeletonHeight(BUDGET_ROWS) }}
    >
      {Array.from({ length: BUDGET_ROWS }, (_, index) => (
        <View
          key={index}
          style={
            index === BUDGET_ROWS - 1 ? styles.budgetRowLast : styles.budgetRow
          }
        >
          <LoadingTile height={17} style={{ marginBottom: space.xs }} />
          <LoadingTile height={6} />
        </View>
      ))}
    </View>
  );
}
