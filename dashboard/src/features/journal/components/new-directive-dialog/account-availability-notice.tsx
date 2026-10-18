import { useId } from "react";
import { Checkbox } from "@/common/components/ui/checkbox";
import { Label } from "@/common/components/ui/label";
import { useTranslations } from "@/common/hooks/use-translations";
import { cn } from "@/common/lib/utils/utils";
import type { useAccountAvailability } from "./use-account-availability";

type AccountAvailabilityCheck = ReturnType<typeof useAccountAvailability>;

/** The inline notice under an account field the ledger would refuse. */
export function AccountAvailabilityNotice({
  check,
  account,
  day,
  className,
}: {
  check: AccountAvailabilityCheck;
  account: string;
  day: string | null;
  className?: string;
}) {
  const { t } = useTranslations();
  const checkboxId = useId();
  const status = check.availability(account, day);
  if (status.kind === "open" || day === null) return null;

  const name = account.trim();
  const opening = check.willOpen(account, day);
  const message =
    status.kind === "unknown"
      ? t("journal.accountNotOpen", { account: name })
      : status.kind === "closed"
        ? t("journal.accountClosedBefore", {
            account: name,
            date: status.closedAt,
          })
        : t("journal.accountOpensAfter", {
            account: name,
            date: status.openedAt,
          });

  return (
    <div role="status" className={cn("space-y-1 text-sm", className)}>
      <p className={cn(opening ? "text-muted-foreground" : "text-destructive")}>
        {message}
      </p>
      {status.kind === "unknown" && status.canOpen && (
        <div className="flex items-center gap-2">
          <Checkbox
            id={checkboxId}
            checked={opening}
            onCheckedChange={(checked) =>
              check.setAlsoOpen(name, checked === true)
            }
          />
          <Label htmlFor={checkboxId} className="font-normal">
            {t("journal.alsoOpenAccount", { account: name, date: day })}
          </Label>
        </div>
      )}
    </div>
  );
}
