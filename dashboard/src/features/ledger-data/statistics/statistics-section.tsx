import { useId, type ComponentType, type ReactNode } from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "@/common/components/ui/button";
import { Table } from "@/common/components/ui/table";
import { useTranslations } from "@/common/hooks/use-translations";

/**
 * The shell every statistics table sits in: heading, description, and the
 * scroll wrappers around the table.
 *
 * Each of these sections renders the shell twice — once while loading and once
 * with data — so the layout existed six times and the accessible name six
 * times with it. Minting the heading id here and putting it on the `Table`
 * makes that naming structural: a section cannot render its table without it.
 */
export function StatisticsSection({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: ComponentType<{ className?: string }>;
  title: ReactNode;
  description: ReactNode;
  /** The table's own header and body rows. */
  children: ReactNode;
}) {
  const headingId = useId();

  return (
    <div>
      <h3
        id={headingId}
        className="flex items-center gap-2 text-lg font-semibold mb-2"
      >
        <Icon className="h-5 w-5" />
        {title}
      </h3>
      <p className="text-sm text-muted-foreground mb-4">{description}</p>
      <div className="overflow-hidden w-full">
        <div className="overflow-x-auto">
          <Table aria-labelledby={headingId}>{children}</Table>
        </div>
      </div>
    </div>
  );
}

/**
 * A section whose read failed: what failed, the classified guidance, and a
 * Try Again that repeats that section's read alone, leaving its siblings as
 * they are (w4/338).
 */
export function StatisticsErrorState({
  description,
  message,
  onRetry,
  retrying,
}: {
  description: ReactNode;
  message: string;
  onRetry: () => void;
  retrying: boolean;
}) {
  const { t } = useTranslations();
  return (
    <div>
      <h3 className="flex items-center gap-2 text-lg font-semibold mb-2">
        <AlertCircle className="h-5 w-5" />
        {t("page.statistics.error")}
      </h3>
      <p className="text-sm text-muted-foreground mb-4">{description}</p>
      <div className="flex items-center justify-center py-12 border rounded-md">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">
            {t("common.failedToLoadData")}
          </h3>
          <p className="text-muted-foreground">{message}</p>
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            loading={retrying}
            className="mt-4"
          >
            {t("common.tryAgain")}
          </Button>
        </div>
      </div>
    </div>
  );
}
