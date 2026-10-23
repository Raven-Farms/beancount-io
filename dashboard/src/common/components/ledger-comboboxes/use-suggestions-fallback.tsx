import { useId, type ReactNode } from "react";
import { NetworkStatus } from "@apollo/client";
import { Button } from "@/common/components/ui/button";
import { useTranslations } from "@/common/hooks/use-translations";

interface SuggestionsQuery {
  error?: unknown;
  networkStatus: NetworkStatus;
  refetch: () => Promise<unknown>;
}

/**
 * A suggestions read only offers options; the value belongs to the parent
 * form (w4/m35). When the read fails the field stays mounted and editable,
 * its options are withheld rather than shown stale, and a notice under it
 * offers an in-place retry. The skeleton is for the first load only, so a
 * retry never remounts the field or drops its focus.
 */
export function useSuggestionsFallback(
  { error, networkStatus, refetch }: SuggestionsQuery,
  hasData: boolean,
  describedBy: string | undefined,
): {
  initialLoading: boolean;
  failed: boolean;
  describedBy: string | undefined;
  notice: ReactNode;
} {
  const { t } = useTranslations();
  const noticeId = useId();
  const retrying = networkStatus === NetworkStatus.refetch;
  const failed = Boolean(error) || (retrying && !hasData);

  return {
    initialLoading:
      networkStatus === NetworkStatus.loading ||
      networkStatus === NetworkStatus.setVariables,
    failed,
    describedBy: failed
      ? [describedBy, noticeId].filter(Boolean).join(" ")
      : describedBy,
    notice: failed ? (
      <p
        id={noticeId}
        className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground"
      >
        {t("component.suggestions.unavailable")}
        <Button
          type="button"
          variant="link"
          size="sm"
          className="h-auto p-0 text-xs"
          loading={retrying}
          onClick={() => void refetch().catch(() => undefined)}
        >
          {t("common.tryAgain")}
        </Button>
      </p>
    ) : undefined,
  };
}
