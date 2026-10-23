import { useQuery } from "@apollo/client/react";
import { useMemo } from "react";
import {
  Combobox,
  type ComboboxFieldProps,
  type ComboboxOption,
} from "@/common/components/ui/combobox";
import { Skeleton } from "@/common/components/ui/skeleton";
import {
  GetLedgerNarrationsDocument,
  type GetLedgerNarrationsQuery,
  type GetLedgerNarrationsQueryVariables,
} from "@/graphql/definitions";
import { useTranslations } from "@/common/hooks/use-translations";
import { useSuggestionsFallback } from "./use-suggestions-fallback";

interface NarrationsComboboxProps extends ComboboxFieldProps {
  ledgerId: string;
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

/**
 * NarrationsCombobox component - searchable combobox for narration selection
 * Uses GetLedgerNarrations GraphQL query to fetch available narrations
 */
export function NarrationsCombobox({
  ledgerId,
  value,
  onValueChange,
  placeholder,
  disabled = false,
  className,
  ...fieldProps
}: NarrationsComboboxProps) {
  const { t } = useTranslations();
  const defaultPlaceholder = placeholder || t("journal.selectNarration");

  const query = useQuery<
    GetLedgerNarrationsQuery,
    GetLedgerNarrationsQueryVariables
  >(GetLedgerNarrationsDocument, {
    variables: { ledgerId },
    skip: !ledgerId,
    notifyOnNetworkStatusChange: true,
  });
  const { data } = query;

  // Convert narrations to ComboboxOption format
  const options: ComboboxOption[] = useMemo(() => {
    if (!data?.getLedgerNarrations) return [];

    return data.getLedgerNarrations.map((narration) => ({
      value: narration,
      label: narration,
    }));
  }, [data]);

  const fallback = useSuggestionsFallback(
    query,
    Boolean(data?.getLedgerNarrations),
    fieldProps["aria-describedby"],
  );

  if (fallback.initialLoading) {
    return <Skeleton className="h-10 w-full" />;
  }

  return (
    <Combobox
      options={fallback.failed ? [] : options}
      value={value}
      onValueChange={onValueChange}
      placeholder={defaultPlaceholder}
      allowCustom={true}
      emptyText={t("journal.noNarrationsFound")}
      disabled={disabled}
      className={className}
      {...fieldProps}
      aria-describedby={fallback.describedBy}
      notice={fallback.notice}
    />
  );
}
