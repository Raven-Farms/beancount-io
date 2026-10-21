import { formatLedgerDate } from "@/common/date-format";
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  useWindowDimensions,
} from "react-native";
import { FadeInView } from "@/components/crossfade";
import { ColorTheme } from "@/types/theme-props";
import {
  fontSizes,
  fontWeights,
  gutter,
  prefersStackedLayout,
  space,
  useTheme,
} from "@/common/theme";
import { useThemeStyle } from "@/common/hooks/use-theme-style";
import { useTranslations } from "@/common/hooks/use-translations";
import {
  formatMoneyWithCurrency,
  formatSignedMoneyWithCurrency,
} from "@/common/number-utils";
import { AmountText, DashboardCard } from "@/components";
import { LoadingTile } from "@/components/loading-tile";
import {
  BudgetBarChartD3,
  LEGEND_HEIGHT,
} from "@/common/d3/budget-bar-chart-d3";
import { useBudgetActuals } from "@/screens/budget-screen/hooks/use-budget-actuals";
import {
  budgetDirection,
  type BudgetGroup,
} from "@/screens/budget-screen/selectors/budget-selectors";
import {
  selectBudgetCardStats,
  selectPointFavorability,
} from "@/screens/budget-screen/selectors/select-budget-card-stats";
import {
  budgetChartSummary,
  intervalLabelKey,
  periodAxisLabel,
  STATUS_LABEL_KEYS,
} from "@/screens/budget-screen/selectors/budget-labels";
import { BudgetHistoryRows } from "@/screens/budget-screen/components/budget-history-rows";
import { BudgetMeter } from "@/screens/budget-screen/components/budget-meter";
import { LEADING_TEXT_ALIGN } from "@/common/rtl";

const CHART_HEIGHT = 190;

const getStyles = (theme: ColorTheme) =>
  StyleSheet.create({
    header: {
      paddingHorizontal: gutter,
      marginBottom: space.md,
    },
    titleRow: {
      flexDirection: "row",
      alignItems: "center",
    },
    // Accessibility text sizes: the account gets the full width and Update
    // Budget moves under it, as DashboardCard stacks its title and action.
    titleStacked: {
      flexDirection: "column",
      alignItems: "flex-start",
    },
    // `flex: 1` sizes the row's title; in a column it would collapse it.
    accountStacked: {
      flex: 0,
      alignSelf: "stretch",
    },
    updateButtonStacked: {
      marginStart: 0,
      marginTop: space.xxs,
    },
    account: {
      flex: 1,
      fontSize: fontSizes.lg,
      fontWeight: fontWeights.medium,
      color: theme.text01,
      textAlign: LEADING_TEXT_ALIGN,
    },
    updateButton: {
      marginStart: space.sm,
      paddingVertical: space.xxs,
    },
    // Matches DashboardCard's "see all" action, the card-level affordance this
    // sits in place of.
    updateText: {
      fontSize: fontSizes.md,
      fontWeight: fontWeights.medium,
      color: theme.primary,
    },
    badgeRow: {
      flexDirection: "row",
      alignItems: "center",
      flexWrap: "wrap",
      marginTop: space.xs,
    },
    badge: {
      borderRadius: 6,
      borderWidth: StyleSheet.hairlineWidth,
      borderColor: theme.black40,
      paddingHorizontal: space.sm,
      paddingVertical: 2,
      marginEnd: space.xs,
      marginTop: space.xxs,
    },
    badgeText: {
      fontSize: fontSizes.xs,
      color: theme.black80,
    },
    statusBadge: {
      borderRadius: 6,
      paddingHorizontal: space.sm,
      paddingVertical: 2,
      marginEnd: space.xs,
      marginTop: space.xxs,
    },
    statusText: {
      fontSize: fontSizes.xs,
      fontWeight: fontWeights.medium,
    },
    stats: {
      flexDirection: "row",
      paddingHorizontal: gutter,
      marginBottom: space.md,
    },
    stat: {
      flex: 1,
    },
    statLabel: {
      fontSize: fontSizes.xs,
      color: theme.black80,
      marginBottom: space.xxs,
      textAlign: LEADING_TEXT_ALIGN,
    },
    statValue: {
      fontSize: fontSizes.lg,
      fontWeight: fontWeights.medium,
      color: theme.text01,
    },
    progressWrap: {
      paddingHorizontal: gutter,
      marginBottom: space.md,
    },
    chartWrap: {
      paddingHorizontal: gutter,
    },
    errorText: {
      paddingHorizontal: gutter,
      fontSize: fontSizes.md,
      color: theme.error,
    },
  });

type BudgetGroupCardProps = {
  group: BudgetGroup;
  ledgerId: string;
  /** Fava time filter for the actuals query; undefined means all time. */
  time?: string;
  /** Opens the form pre-filled to add a newer-dated entry for this budget. */
  onUpdate?: (group: BudgetGroup) => void;
};

/**
 * One card per account+currency budget: the numbers that answer "am I on
 * track?" up top, then the period-by-period chart behind them.
 */
export function BudgetGroupCard({
  group,
  ledgerId,
  time,
  onUpdate,
}: BudgetGroupCardProps): JSX.Element {
  const styles = useThemeStyle(getStyles);
  const theme = useTheme().colorTheme;
  const { t, locale } = useTranslations();
  // At AX2 the row left the account a few letters — "Ex…ing", "Ex…ries" —
  // so budgets could not be told apart (w21/027).
  const { fontScale } = useWindowDimensions();
  const stacked = prefersStackedLayout(fontScale);

  const direction = budgetDirection(group.value);
  const { currency } = group;

  const { series, loading, error } = useBudgetActuals({
    ledgerId,
    group,
    currency,
    time,
    direction,
  });

  const stats = selectBudgetCardStats(group, series);
  const favorables = selectPointFavorability(
    series,
    direction,
    group.budgetHistory,
  );

  // One object so the chart and its spoken summary can never describe different
  // series.
  const chartSeries = {
    labels: series.map((point) =>
      periodAxisLabel(point.date, group.interval, t, locale),
    ),
    actuals: series.map((point) => point.actual),
    budgets: series.map((point) => point.budget),
    favorables,
    currency,
  };

  const formatAmount = (value: number) =>
    formatMoneyWithCurrency(value, currency);

  const statusColor = stats.favorable ? theme.success : theme.error;

  return (
    // `bleed`: every section below applies its own gutter so the chart and the
    // history rows can run edge to edge.
    <DashboardCard bleed>
      <View style={styles.header}>
        <View style={[styles.titleRow, stacked && styles.titleStacked]}>
          <Text
            // Remeasured on a live size change (mobile/AGENTS.md).
            key={`account-${fontScale}`}
            style={[styles.account, stacked && styles.accountStacked]}
            numberOfLines={stacked ? 2 : 1}
            // Stacked, the leaf is what tells two budgets apart.
            ellipsizeMode={stacked ? "head" : "middle"}
          >
            {group.account}
          </Text>
          {onUpdate && (
            <TouchableOpacity
              style={[
                styles.updateButton,
                stacked && styles.updateButtonStacked,
              ]}
              onPress={() => onUpdate(group)}
              accessibilityRole="button"
              // Which budget: every card's button read "Update" (w21/142).
              accessibilityLabel={t("budgetUpdateNamed", {
                account: group.account,
                currency,
              })}
            >
              <Text style={styles.updateText}>{t("budgetUpdate")}</Text>
            </TouchableOpacity>
          )}
        </View>
        <View style={styles.badgeRow}>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>
              {t(intervalLabelKey(group.interval))}
            </Text>
          </View>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{currency}</Text>
          </View>
          {stats.startsOn !== null && (
            // Not yet in effect: neutral, never "Above target" (w21/101).
            <View
              style={[
                styles.statusBadge,
                { backgroundColor: theme.black20, borderColor: theme.black60 },
              ]}
            >
              <Text style={[styles.statusText, { color: theme.black80 }]}>
                {t("budgetStartsOn", {
                  date: formatLedgerDate(stats.startsOn, locale),
                })}
              </Text>
            </View>
          )}
          {stats.status !== null && (
            <View
              style={[
                styles.statusBadge,
                { backgroundColor: theme.black20, borderColor: statusColor },
              ]}
            >
              <Text style={[styles.statusText, { color: statusColor }]}>
                {t(STATUS_LABEL_KEYS[stats.status])}
              </Text>
            </View>
          )}
        </View>
      </View>

      <View style={styles.stats}>
        <View style={styles.stat}>
          <Text style={styles.statLabel}>{t("budget")}</Text>
          <AmountText style={styles.statValue}>
            {formatAmount(stats.budget)}
          </AmountText>
        </View>
        {stats.actual !== null && (
          <View style={styles.stat}>
            <Text style={styles.statLabel}>{t("budgetActual")}</Text>
            <AmountText style={styles.statValue}>
              {formatAmount(stats.actual)}
            </AmountText>
          </View>
        )}
        {stats.variance !== null && (
          <View style={styles.stat}>
            <Text style={styles.statLabel}>{t("budgetVariance")}</Text>
            <AmountText style={[styles.statValue, { color: statusColor }]}>
              {formatSignedMoneyWithCurrency(stats.variance, currency, true)}
            </AmountText>
          </View>
        )}
      </View>

      {stats.progressPercent !== null && (
        <View style={styles.progressWrap}>
          <BudgetMeter
            percent={stats.progressPercent}
            favorable={stats.favorable}
          />
        </View>
      )}

      <View style={styles.chartWrap}>
        {loading && series.length === 0 ? (
          <LoadingTile height={CHART_HEIGHT + LEGEND_HEIGHT} />
        ) : error ? (
          <Text style={styles.errorText}>{t("budgetLoadFailed")}</Text>
        ) : (
          <FadeInView>
            <BudgetBarChartD3
              {...chartSeries}
              accessibilityLabel={budgetChartSummary(chartSeries, t, locale)}
              height={CHART_HEIGHT}
            />
          </FadeInView>
        )}
      </View>

      <BudgetHistoryRows group={group} ledgerId={ledgerId} />
    </DashboardCard>
  );
}
