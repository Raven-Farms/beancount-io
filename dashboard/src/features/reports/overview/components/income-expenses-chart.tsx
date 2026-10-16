import { ReactECharts } from "@/common/components/react-echarts";
import { defaultSplitLine } from "@/common/components/react-echarts/utils";
import { useFormatNumber } from "@/common/hooks/use-format-number";
import { useTranslations } from "@/common/hooks/use-translations";
import { CONFINED_TOOLTIP } from "@/common/lib/chart/tooltip";
import { type DataSeries } from "../lib/overview-utils";
import {
  balanceToAmounts,
  chooseDisplayUnit,
  collectUnits,
} from "../lib/unit-amounts";
import { ChartUnitScope } from "./chart-unit-scope";
import { ChartDataTable } from "../../components/chart-data-table";
import { Amount } from "@/common/components/amount";
import {
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/common/components/ui/table";

export function IncomeExpensesChart({
  income,
  expenses,
  primaryCurrency,
}: {
  income: DataSeries;
  expenses: DataSeries;
  /** The ledger's operating currency, preferred as the chart's unit. */
  primaryCurrency?: string | null;
}) {
  const { t } = useTranslations();
  const formatNum = useFormatNumber();
  const dates: string[] =
    (income?.length ? income : expenses)?.map((d) => d.date) ?? [];
  // Bars are compared against each other down a single axis, so this chart is
  // in the same position as the others: one unit, and say what it leaves out.
  const incomeAmounts = income?.map((d) => balanceToAmounts(d.balance)) ?? [];
  const expenseAmounts =
    expenses?.map((d) => balanceToAmounts(d.balance)) ?? [];
  const allAmounts = [...incomeAmounts, ...expenseAmounts];
  const unit = chooseDisplayUnit(allAmounts, primaryCurrency);
  const units = collectUnits(allAmounts);
  const inUnit = (amounts: Map<string, number>) =>
    unit ? (amounts.get(unit) ?? 0) : 0;
  const incomeValues = incomeAmounts.map(inUnit);
  const expensesValues = expenseAmounts.map(inUnit);

  const isEmpty =
    !incomeValues.some((v) => v !== 0) && !expensesValues.some((v) => v !== 0);

  const option = {
    tooltip: {
      ...CONFINED_TOOLTIP,
      trigger: "axis" as const,
      axisPointer: { type: "shadow" as const },
      valueFormatter: (value: unknown) =>
        typeof value === "number"
          ? formatNum(value === 0 ? 0 : value)
          : String(value),
    },
    legend: {
      data: [t("common.income"), t("common.expenses")],
      bottom: 0,
      type: "scroll" as const,
    },
    grid: {
      left: "0%",
      right: "0%",
      bottom: "25px",
      top: "10px",
      containLabel: true,
    },
    xAxis: { type: "category" as const, data: dates },
    yAxis: {
      type: "value" as const,
      axisLabel: {
        formatter: (v: number) => (typeof v === "number" ? formatNum(v) : v),
      },
      splitLine: defaultSplitLine,
    },
    series: [
      {
        name: t("common.income"),
        type: "bar" as const,
        data: incomeValues.map((v) => -v),
        emphasis: { focus: "series" as const },
      },
      {
        name: t("common.expenses"),
        type: "bar" as const,
        data: expensesValues,
        emphasis: { focus: "series" as const },
      },
    ],
    animation: true,
    animationDuration: 800,
  };

  return (
    <div className="w-full">
      <ReactECharts
        option={option}
        isEmpty={isEmpty}
        style={{ height: "250px", width: "100%" }}
        className="w-full"
      />
      <ChartUnitScope unit={unit} units={units} />
      {unit && dates.length > 0 && (
        <ChartDataTable
          label={t("page.reports.incomeVsExpenses")}
          summary={t("page.accountReport.periodData")}
        >
          <TableHeader>
            <TableRow>
              <TableHead scope="col">
                {t("page.accountReport.period")}
              </TableHead>
              <TableHead scope="col" className="text-end">
                {t("common.income")}
              </TableHead>
              <TableHead scope="col" className="text-end">
                {t("common.expenses")}
              </TableHead>
              <TableHead scope="col" className="text-end">
                {t("common.netProfit")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {option.xAxis.data.map((date, index) => {
              const income = option.series[0].data[index];
              const expenses = option.series[1].data[index];
              const net =
                income === undefined || expenses === undefined
                  ? undefined
                  : income - expenses;
              return (
                <TableRow key={date}>
                  <TableHead
                    scope="row"
                    className="whitespace-nowrap font-mono text-xs tabular-nums"
                  >
                    {date}
                  </TableHead>
                  {[income, expenses, net].map((value, column) => (
                    <TableCell
                      key={column}
                      className="text-end font-mono text-sm tabular-nums"
                    >
                      {value === undefined ? (
                        "—"
                      ) : (
                        <Amount>
                          {String(value)} {unit}
                        </Amount>
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })}
          </TableBody>
        </ChartDataTable>
      )}
    </div>
  );
}
