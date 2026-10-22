import { useEffect } from "react";
import { useRouter } from "expo-router";
import { StyleSheet, Text, useWindowDimensions } from "react-native";
import { ColorTheme } from "@/types/theme-props";
import { fontSizes } from "@/common/theme";
import { LEADING_TEXT_ALIGN } from "@/common/rtl";
import { useThemeStyle } from "@/common/hooks/use-theme-style";
import { useTranslations } from "@/common/hooks/use-translations";
import { LoadingTile } from "@/components/loading-tile";
import { DashboardCard } from "@/components";
import { FadeInView } from "@/components/crossfade";
import { BAR_CHART_HEIGHT, BarChartD3 } from "@/common/d3/bar-chart-d3";
import {
  useGetLedgerIntervalTotalsQuery,
  useLedgerReadContextQuery,
} from "@/generated-graphql/graphql";
import {
  noSpending,
  selectSpendingCompare,
  spendingChartSummary,
  spendingTotalsCaption,
  spendingWindow,
} from "@/screens/home-screen/selectors/select-spending-compare";
import { CardLoadFailure } from "@/components/card-load-failure";
import {
  selectCardLoadState,
  selectReadContextState,
} from "@/common/apollo/card-load-state";
import { useGuest } from "@/common/guest/guest-context";
import { getFormatDate } from "@/common/format-util";
import { useScheduledThisMonth } from "@/screens/home-screen/hooks/use-scheduled-this-month";
import {
  monthToDateWindow,
  withMonthToDate,
} from "@/screens/home-screen/selectors/scheduled-this-month";
import { formatHolding, notInTotalNotes } from "@/common/balance-display";
import { isolateLtr } from "@/common/bidi";

// Static x-axis labels (translation keys) for the two comparison bars.
const SPENDING_LABELS = ["lastMonth", "thisMonth"];

const getStyles = (theme: ColorTheme) =>
  StyleSheet.create({
    subtitle: {
      paddingHorizontal: 16,
      marginBottom: 12,
      fontSize: fontSizes.sm,
      color: theme.black80,
      textAlign: LEADING_TEXT_ALIGN,
    },
    totals: {
      paddingHorizontal: 16,
      marginTop: 8,
      fontSize: fontSizes.sm,
      color: theme.text01,
      textAlign: LEADING_TEXT_ALIGN,
    },
    empty: {
      paddingHorizontal: 16,
      paddingVertical: 24,
      fontSize: fontSizes.md,
      color: theme.black80,
      textAlign: LEADING_TEXT_ALIGN,
    },
    note: {
      paddingHorizontal: 16,
      marginTop: 8,
      fontSize: fontSizes.sm,
      color: theme.black80,
      textAlign: LEADING_TEXT_ALIGN,
    },
  });

type SpendingCardProps = {
  ledgerId?: string;
  currency: string;
  refreshSignal?: number;
};

/**
 * "Spending" card comparing this month's total spending against last month's,
 * from the Expenses root's monthly totals over those two months.
 */
export function SpendingCard({
  ledgerId,
  currency,
  refreshSignal = 0,
}: SpendingCardProps): JSX.Element {
  const styles = useThemeStyle(getStyles);
  const { t } = useTranslations();
  // Keyed on the text size: iOS keeps a Text's old measurement when it
  // changes with the app open (mobile/AGENTS.md; w21/015).
  const { fontScale } = useWindowDimensions();
  const router = useRouter();
  const guest = useGuest();

  // `navigate` rather than `push`: Reports is a tab, so this switches to it and
  // leaves Home on its own stack with its scroll position intact.
  const openReports = () => {
    if (guest) {
      guest.navigate("reports");
      return;
    }
    router.navigate({ pathname: "/reports" });
  };

  // The ledger may rename its roots (`option "name_expenses"`); the shared
  // read context carries the real name. Wait for it rather than query a root
  // the ledger may not have.
  const context = useLedgerReadContextQuery({
    variables: { ledgerId: ledgerId! },
    skip: !ledgerId,
  });
  // The currency and roots come from the context: holding until it lands (and
  // failing the card when it cannot) keeps a EUR ledger from rendering in the
  // "USD" fallback (w21/262).
  const contextState = selectReadContextState(context.data, context.error);
  const contextSettled = contextState === "ready";
  const expensesRoot =
    context.data?.getLedger.options.nameExpenses || "Expenses";

  // Both months whole, however many transactions they hold: the newest 200
  // journal rows used to stand in for them (w21/011).
  const { data, loading, error, refetch } = useGetLedgerIntervalTotalsQuery({
    variables: {
      ledgerId: ledgerId!,
      accountName: expensesRoot,
      interval: "month",
      conversion: "units",
      time: spendingWindow(),
    },
    skip: !ledgerId || !contextSettled,
    fetchPolicy: "cache-and-network",
  });

  useEffect(() => {
    if (refreshSignal > 0 && ledgerId) {
      void refetch().catch(() => undefined);
    }
  }, [refreshSignal, ledgerId, refetch]);

  // Entries pre-entered for later this month are not spent yet: when there are
  // any, this month is read to today (w21/337). Guests have no such entries,
  // and the statement is not one an example may run.
  const today = getFormatDate(new Date());
  const scheduled = useScheduledThisMonth(ledgerId, today, Boolean(guest));
  const toToday = useGetLedgerIntervalTotalsQuery({
    variables: {
      ledgerId: ledgerId!,
      accountName: expensesRoot,
      interval: "month",
      conversion: "units",
      time: monthToDateWindow(today),
    },
    skip: !ledgerId || !contextSettled || !scheduled,
    fetchPolicy: "cache-and-network",
  });
  const months = withMonthToDate(
    data?.getLedgerIntervalTotals ?? [],
    scheduled ? toToday.data?.getLedgerIntervalTotals : undefined,
    today,
  );
  const { thisMonth, lastMonth, notInTotal, lastMonthNotInTotal } =
    selectSpendingCompare(months, currency);
  const [note] = notInTotalNotes(notInTotal, t);
  // Last month's own, so a refund then does not cancel this month's spending.
  const lastNote =
    lastMonthNotInTotal.length > 0
      ? t("spendingLastMonthNotInTotal", {
          amounts: lastMonthNotInTotal
            .map((holding) => isolateLtr(formatHolding(holding)))
            .join(", "),
        })
      : null;

  return (
    <DashboardCard
      title={t("spending")}
      onSeeAll={openReports}
      bleed
      testID="spending-card"
    >
      <Text key={`subtitle-${fontScale}`} style={styles.subtitle}>
        {t("spendingSubtitle")}
      </Text>
      {contextState === "failed" ||
      selectCardLoadState({
        loading: loading || !contextSettled,
        hasData: data !== undefined,
        error: error,
      }) === "failed" ? (
        <CardLoadFailure
          onRetry={() =>
            void Promise.all([
              context.refetch(),
              contextSettled ? refetch() : Promise.resolve(),
            ]).catch(() => undefined)
          }
        />
      ) : (loading || !contextSettled) && data === undefined ? (
        <LoadingTile height={BAR_CHART_HEIGHT} mx={16} />
      ) : (
        <FadeInView>
          {noSpending({ lastMonth, thisMonth }) ? (
            // Two 2 pt bars over a $0 to $1 axis suggested cents of spending.
            <Text
              key={`empty-${fontScale}`}
              testID="spending-empty"
              style={styles.empty}
            >
              {t("spendingEmpty")}
            </Text>
          ) : (
            <>
              <BarChartD3
                currency={currency}
                labels={SPENDING_LABELS}
                numbers={[lastMonth, thisMonth]}
                accessibilityLabel={spendingChartSummary(
                  { lastMonth, thisMonth },
                  currency,
                  t,
                  note,
                )}
              />
              {/* The chart's label already speaks the amounts. */}
              <Text
                key={`totals-${fontScale}`}
                testID="spending-totals"
                style={styles.totals}
                accessibilityElementsHidden
                importantForAccessibility="no-hide-descendants"
              >
                {spendingTotalsCaption(
                  { lastMonth, thisMonth },
                  currency,
                  { thisMonth: t("thisMonth"), lastMonth: t("lastMonth") },
                  isolateLtr,
                )}
              </Text>
            </>
          )}
          {note ? (
            <Text
              key={`note-${fontScale}`}
              testID="spending-not-in-total"
              style={styles.note}
            >
              {note}
            </Text>
          ) : null}
          {lastNote ? (
            <Text
              key={`last-note-${fontScale}`}
              testID="spending-last-not-in-total"
              style={styles.note}
            >
              {lastNote}
            </Text>
          ) : null}
        </FadeInView>
      )}
    </DashboardCard>
  );
}
