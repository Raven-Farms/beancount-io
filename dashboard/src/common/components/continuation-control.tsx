import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/common/components/ui/button";
import { useTranslations } from "@/common/hooks/use-translations";

interface ContinuationControlProps {
  hasMore: boolean;
  loading: boolean;
  itemCount: number;
  onLoadMore: () => Promise<void>;
  label: string;
  errorMessage?: string;
  retryLabel?: string;
  loadingLabel?: string;
  loadedCount?: number | null;
  formatLoaded?: (count: number) => string;
  getEndFocusTarget?: (previousCount: number) => HTMLElement | null | undefined;
  icon?: ReactNode;
  className?: string;
  buttonClassName?: string;
}

/** A continuation stays in the tab order while its request is in flight. */
export function ContinuationControl({
  hasMore,
  loading,
  itemCount,
  onLoadMore,
  label,
  errorMessage,
  retryLabel,
  loadingLabel,
  loadedCount,
  formatLoaded,
  getEndFocusTarget,
  icon,
  className,
  buttonClassName,
}: ContinuationControlProps) {
  const { t } = useTranslations();
  const button = useRef<HTMLButtonElement>(null);
  const status = useRef<HTMLParagraphElement>(null);
  const pending = useRef(false);
  const active = useRef(false);
  const ownsFocus = useRef(false);
  const [requestPending, setRequestPending] = useState(false);
  const [completedFrom, setCompletedFrom] = useState<number | null>(null);
  const [lastLoaded, setLastLoaded] = useState<number | null>(null);
  const busy = loading || requestPending;

  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);

  useLayoutEffect(() => {
    if (busy || completedFrom === null) return;
    // Apollo can publish the page metadata just before the merged list renders.
    if (
      !errorMessage &&
      loadedCount != null &&
      itemCount < completedFrom + loadedCount
    ) {
      return;
    }
    if (!errorMessage) {
      setLastLoaded(loadedCount ?? Math.max(0, itemCount - completedFrom));
    }
    if (
      !hasMore &&
      !errorMessage &&
      ownsFocus.current &&
      (document.activeElement === button.current ||
        document.activeElement === document.body)
    ) {
      (getEndFocusTarget?.(completedFrom) ?? status.current)?.focus();
    }
    ownsFocus.current = false;
    setCompletedFrom(null);
  }, [
    busy,
    completedFrom,
    errorMessage,
    getEndFocusTarget,
    hasMore,
    itemCount,
    loadedCount,
  ]);

  const loadMore = async () => {
    // The ref closes the interval before React commits loading state.
    if (pending.current || loading || (!hasMore && !errorMessage)) return;
    pending.current = true;
    ownsFocus.current = document.activeElement === button.current;
    setRequestPending(true);
    setCompletedFrom(null);
    const previousCount = itemCount;
    try {
      await onLoadMore();
    } finally {
      pending.current = false;
      if (active.current) {
        setRequestPending(false);
        setCompletedFrom(previousCount);
      }
    }
  };

  const loadedMessage =
    lastLoaded === null
      ? ""
      : (formatLoaded?.(lastLoaded) ??
        t("common.moreItemsLoaded", { count: lastLoaded }));

  return (
    <div className={className}>
      {errorMessage && (
        <p role="alert" className="text-center text-sm text-destructive">
          {errorMessage}
        </p>
      )}
      {(hasMore || !!errorMessage || busy) && (
        <Button
          ref={button}
          variant="outline"
          className={buttonClassName}
          aria-disabled={busy}
          onClick={() => void loadMore()}
          onBlur={() => {
            ownsFocus.current = false;
          }}
          onFocus={() => {
            if (pending.current) ownsFocus.current = true;
          }}
        >
          {busy ? (
            <Loader2 className="mr-2 size-4 animate-spin" aria-hidden="true" />
          ) : (
            icon
          )}
          {busy && loadingLabel
            ? loadingLabel
            : errorMessage
              ? (retryLabel ?? label)
              : label}
        </Button>
      )}
      <p
        ref={status}
        role="status"
        aria-live="polite"
        aria-atomic="true"
        tabIndex={-1}
        className="text-center text-sm text-muted-foreground"
      >
        {busy
          ? t("common.loading")
          : !errorMessage && (
              <>
                {loadedMessage}
                {!hasMore && (
                  <>
                    {loadedMessage && " "}
                    {t("common.noMoreResults")}
                  </>
                )}
              </>
            )}
      </p>
    </div>
  );
}
