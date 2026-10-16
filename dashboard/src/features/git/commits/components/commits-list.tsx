import { useEffect, useId, useRef } from "react";
import { useTranslations } from "@/common/hooks/use-translations";
import { getErrorMessageKey } from "@/common/lib/errors/error-message";
import { Skeleton } from "@/common/components/ui/skeleton";
import { Alert, AlertDescription } from "@/common/components/ui/alert";
import { CommitListItem } from "./commit-list-item";
import type { ListCommitsQuery } from "@/graphql/definitions";
import { Button } from "@/common/components/ui/button";

interface CommitsListProps {
  ledgerId: string;
  selectedCommitSha?: string;
  onCommitSelect?: (sha: string) => void;
  commits: ListCommitsQuery["listCommits"];
  loading: boolean;
  error?: Error;
  hasMore: boolean;
  loadingMore: boolean;
  paginationError: boolean;
  loadedOlderCount: number | null;
  onLoadMore: () => Promise<void>;
}

export function CommitsList({
  ledgerId,
  selectedCommitSha,
  onCommitSelect,
  commits,
  loading,
  error,
  hasMore,
  loadingMore,
  paginationError,
  loadedOlderCount,
  onLoadMore,
}: CommitsListProps) {
  const { t } = useTranslations();
  const titleId = useId();
  const section = useRef<HTMLElement>(null);
  const loadButton = useRef<HTMLButtonElement>(null);
  const restoreFocus = useRef<number | null>(null);

  useEffect(() => {
    if (loadingMore || restoreFocus.current === null) return;
    if (
      !hasMore &&
      loadedOlderCount !== null &&
      commits.length < restoreFocus.current + loadedOlderCount
    ) {
      return;
    }
    if (
      document.activeElement !== loadButton.current &&
      document.activeElement !== document.body
    ) {
      restoreFocus.current = null;
      return;
    }
    if (hasMore) {
      loadButton.current?.focus();
    } else {
      const links =
        section.current?.querySelectorAll<HTMLAnchorElement>("nav a");
      links?.[Math.min(restoreFocus.current, links.length - 1)]?.focus();
    }
    restoreFocus.current = null;
  }, [loadingMore, hasMore, commits.length, loadedOlderCount]);

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{t(getErrorMessageKey(error))}</AlertDescription>
      </Alert>
    );
  }

  if (loading) {
    return (
      <section aria-label={t("commits.listTitle")}>
        <div className="flex h-10 items-center border-b border-border px-3">
          <Skeleton className="h-4 w-20" />
        </div>
        <div className="divide-y divide-border" aria-hidden="true">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="flex h-[60px] items-center gap-2.5 px-3">
              <Skeleton className="size-4 shrink-0 rounded-full" />
              <div className="min-w-0 flex-1 space-y-1.5">
                <Skeleton className="h-3.5 w-4/5" />
                <Skeleton className="h-3 w-3/5" />
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section ref={section} className="min-w-0" aria-labelledby={titleId}>
      <header className="flex h-10 items-center border-b border-border px-3">
        <h2 id={titleId} className="text-sm font-semibold">
          {t("commits.listTitle")}
        </h2>
      </header>
      {selectedCommitSha &&
        !commits.some((commit) => commit.sha === selectedCommitSha) && (
          <p className="border-b border-border p-3 text-sm text-muted-foreground">
            {t("commits.selectedOutsideHistory")}
          </p>
        )}
      <nav aria-label={t("commits.versionHistory")}>
        <ul className="divide-y divide-border">
          {commits.map((commit) => (
            <li key={commit.sha} className="min-w-0">
              <CommitListItem
                commit={commit}
                ledgerId={ledgerId}
                isSelected={commit.sha === selectedCommitSha}
                onSelect={onCommitSelect}
              />
            </li>
          ))}
        </ul>
      </nav>
      {commits.length === 0 && (
        <p className="flex h-[60px] items-center px-3 text-sm text-muted-foreground">
          {t("commits.noCommits")}
        </p>
      )}
      <p role="status" className="sr-only">
        {loadedOlderCount !== null &&
          t("commits.loadedOlder", { count: loadedOlderCount })}
      </p>
      {hasMore && (
        <div className="space-y-2 p-3">
          {paginationError && (
            <p role="alert" className="text-sm text-destructive">
              {t("common.failedToLoadData")}
            </p>
          )}
          <Button
            ref={loadButton}
            variant="outline"
            className="w-full"
            disabled={loadingMore}
            onClick={() => {
              restoreFocus.current = commits.length;
              void onLoadMore();
            }}
          >
            {t(loadingMore ? "common.loading" : "commits.loadOlder")}
          </Button>
        </div>
      )}
    </section>
  );
}
