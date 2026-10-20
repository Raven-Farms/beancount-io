import { useRef, useState } from "react";
import {
  Link,
  useBlocker,
  useNavigate,
  useParams,
} from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { PageHeader } from "@/common/components/page-header";
import { Button } from "@/common/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/common/components/ui/dialog";
import { useLedger } from "@/common/hooks/use-ledger";
import { useTranslations } from "@/common/hooks/use-translations";
import { createLedgerId } from "@/common/lib/utils/encode";
import { EntryContextPanel } from "@/features/journal/components/entry-context-panel";

/**
 * Canonical destination for native Share/Copy entry URLs
 * (`/ledger/<owner>/<ledger>/entry/<hash>`). Reuses journal entry-context
 * presentation without paging the whole journal.
 */
export default function EntryPage() {
  const { t } = useTranslations();
  const navigate = useNavigate();
  const { ledgerOwner, ledgerName, entryHash } = useParams({
    from: "/ledger/$ledgerOwner/$ledgerName/entry/$entryHash",
  });
  const ledgerId = createLedgerId(ledgerOwner, ledgerName);
  const { ledgerName: ledgerDisplayName } = useLedger();

  // Unsaved source edits guard every exit from this page — Back to journal,
  // the source-file action, any other link — as the Journal dialog does
  // (w4/250). A completed delete leaves without asking.
  const [dirty, setDirty] = useState(false);
  const leavingRef = useRef(false);
  const blocker = useBlocker({
    shouldBlockFn: () => dirty && !leavingRef.current,
    enableBeforeUnload: () => dirty,
    withResolver: true,
  });

  const journalHref = {
    to: "/ledger/$ledgerOwner/$ledgerName/journal" as const,
    params: { ledgerOwner, ledgerName },
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <PageHeader
          title={t("journal.entryPageTitle")}
          description={t("journal.entryPageDescription", {
            ledgerName: ledgerDisplayName ?? ledgerName,
          })}
        />
        <Button variant="outline" size="sm" className="self-start" asChild>
          <Link {...journalHref}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t("journal.backToJournal")}
          </Link>
        </Button>
      </div>

      <div className="overflow-hidden rounded-xl border bg-card p-4 shadow-sm sm:p-6">
        <EntryContextPanel
          key={`${ledgerId}:${entryHash}`}
          entryHash={entryHash}
          ledgerId={ledgerId}
          onDirtyChange={setDirty}
          onDeleted={() => {
            leavingRef.current = true;
            void navigate(journalHref);
          }}
        />
      </div>

      <Dialog
        open={blocker.status === "blocked"}
        onOpenChange={(open) => !open && blocker.reset?.()}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t("journal.discardEntryEditTitle")}</DialogTitle>
            <DialogDescription>
              {t("journal.discardEntryEditDescription")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex-col gap-2 sm:flex-row">
            <Button variant="outline" onClick={() => blocker.reset?.()}>
              {t("journal.keepEditing")}
            </Button>
            <Button variant="destructive" onClick={() => blocker.proceed?.()}>
              {t("journal.discardEntryEdit")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
