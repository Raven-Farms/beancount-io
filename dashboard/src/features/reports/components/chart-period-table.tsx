import { useId } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/common/components/ui/table";
import { useTranslations } from "@/common/hooks/use-translations";
import { Amount } from "@/common/components/amount";

/** A plotted point: a date and whatever units it holds. */
interface ChartPeriodPoint {
  date: string;
  balance: Record<string, unknown>;
}

/** Already-computed plotted values; account segments share their unit column. */
export interface ChartPeriodSeries {
  unit: string;
  account?: string;
  values: number[];
}

type ChartPeriodTableProps = {
  labelledBy: string;
} & (
  | { data: ChartPeriodPoint[]; series?: undefined }
  | { data: Array<{ date: string }>; series: ChartPeriodSeries[] }
);

/**
 * Account charts retain source quantities and distinguish absent balances
 * from zero. Statement charts provide their computed series instead, including
 * plotted zero-fill and sign inversion, with one column per unit. Stacked
 * account segments remain separately labelled rather than summed across units.
 */
export function ChartPeriodTable({
  data,
  labelledBy,
  series,
}: ChartPeriodTableProps) {
  const { t } = useTranslations();
  const summaryId = useId();
  const unitSeries = series?.reduce((groups, item) => {
    const segments = groups.get(item.unit);
    if (segments) segments.push(item);
    else groups.set(item.unit, [item]);
    return groups;
  }, new Map<string, ChartPeriodSeries[]>());

  if (data.length === 0) return null;

  return (
    <details className="mt-4 rounded-lg border">
      <summary
        id={summaryId}
        className="cursor-pointer list-none px-3 py-2 text-sm font-medium text-muted-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        {t("page.accountReport.periodData")}
      </summary>
      <div className="overflow-x-auto border-t">
        <Table aria-labelledby={`${labelledBy} ${summaryId}`}>
          <TableHeader className="bg-muted/40">
            <TableRow className="hover:bg-transparent">
              <TableHead className="min-w-28">
                {t("page.accountReport.period")}
              </TableHead>
              {unitSeries ? (
                Array.from(unitSeries.keys(), (unit) => (
                  <TableHead
                    key={unit}
                    scope="col"
                    className="min-w-28 text-end"
                  >
                    {unit}
                  </TableHead>
                ))
              ) : (
                <TableHead className="min-w-28 text-right">
                  {t("page.accountReport.periodAmount")}
                </TableHead>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((point, index) => {
              if (unitSeries) {
                return (
                  <TableRow key={point.date}>
                    <TableHead
                      scope="row"
                      className="whitespace-nowrap font-mono text-xs tabular-nums"
                    >
                      {point.date}
                    </TableHead>
                    {Array.from(unitSeries, ([unit, segments]) => (
                      <TableCell
                        key={unit}
                        className="text-end font-mono text-sm tabular-nums"
                      >
                        {segments.map((item, segment) => (
                          <div key={segment} className="whitespace-nowrap">
                            {item.account && <span>{item.account}: </span>}
                            <Amount>
                              {String(item.values[index])} {unit}
                            </Amount>
                          </div>
                        ))}
                      </TableCell>
                    ))}
                  </TableRow>
                );
              }
              const balances = Object.entries(
                (point as ChartPeriodPoint).balance,
              ).filter(([, value]) => value !== null && value !== undefined);
              return (
                <TableRow key={point.date}>
                  <TableCell className="whitespace-nowrap font-mono text-xs tabular-nums">
                    {point.date}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums">
                    {balances.length === 0
                      ? "—"
                      : balances.map(([currency, value]) => (
                          <div key={currency} className="whitespace-nowrap">
                            {String(value)} {currency}
                          </div>
                        ))}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </details>
  );
}
