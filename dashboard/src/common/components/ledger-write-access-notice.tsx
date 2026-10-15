import { Link, useLocation } from "@tanstack/react-router";
import { LockKeyhole } from "lucide-react";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/common/components/ui/alert";
import { buttonVariants } from "@/common/components/ui/button";
import { useIsAuthenticated } from "@/common/hooks/use-is-authenticated";
import { useLedger } from "@/common/hooks/use-ledger";
import { useTranslations } from "@/common/hooks/use-translations";
import { getSafeReturnPath } from "@/common/lib/auth/auth";

type LedgerWriteAccessNoticeProps = {
  title: string;
  /** Signed-out visitor: invite them to sign in and come back here. */
  signedOut: string;
  /** Signed-in reader without push/admin permission. */
  readOnly: string;
  /** Signed-in user whose ledger permissions could not be read. */
  unresolved: string;
};

/**
 * Shown in place of a write-only workflow (import, receipt upload) when the
 * viewer cannot write to the ledger. Each state says what would let them in.
 */
export function LedgerWriteAccessNotice({
  title,
  signedOut,
  readOnly,
  unresolved,
}: LedgerWriteAccessNoticeProps) {
  const { t } = useTranslations();
  const isAuthenticated = useIsAuthenticated();
  const { ledgerData } = useLedger();
  const location = useLocation();

  if (!isAuthenticated) {
    return (
      <Alert role="status">
        <LockKeyhole aria-hidden />
        <AlertTitle>{title}</AlertTitle>
        <AlertDescription>
          <p>{signedOut}</p>
          <Link
            to="/auth/login"
            search={{ next: getSafeReturnPath(location) }}
            className={buttonVariants({ size: "sm", className: "mt-2" })}
          >
            {t("common.writeAccess.signIn")}
          </Link>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Alert role="status">
      <LockKeyhole aria-hidden />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        {ledgerData.permissions ? readOnly : unresolved}
      </AlertDescription>
    </Alert>
  );
}
