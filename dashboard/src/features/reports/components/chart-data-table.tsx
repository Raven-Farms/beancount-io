import { useId, type ReactNode } from "react";
import { Table } from "@/common/components/ui/table";

/** The same native, named disclosure for chart text alternatives. */
export function ChartDataTable({
  summary,
  labelledBy,
  label,
  children,
}: {
  summary: string;
  children: ReactNode;
} & (
  | { labelledBy: string; label?: never }
  | { label: string; labelledBy?: never }
)) {
  const summaryId = useId();
  return (
    <details className="mt-4 rounded-lg border">
      <summary
        id={summaryId}
        className="cursor-pointer list-none px-3 py-2 text-sm font-medium text-muted-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        {summary}
      </summary>
      <div className="overflow-x-auto border-t">
        <Table
          aria-labelledby={
            labelledBy ? `${labelledBy} ${summaryId}` : undefined
          }
          aria-label={label ? `${label} ${summary}` : undefined}
        >
          {children}
        </Table>
      </div>
    </details>
  );
}
