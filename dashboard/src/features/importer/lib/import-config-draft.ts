import type { ParsedRow } from "../types";
import { parseAmount, parseDate } from "../utils/csv-validator";

/** Per-row choices retained across Configure ↔ Preview transitions. */
export type ImportConfigRowDraft = {
  targetAccount: string;
  selected: boolean;
};

/**
 * Configuration draft for the active import file. Keyed by ParsedRow.id so
 * preview edits/deletions cannot shift one row's mapping onto another.
 * Financial fields always come from the latest parse — never from the draft.
 */
export type ImportConfigDraft = {
  sourceAccount: string;
  defaultCurrency: string;
  rows: Record<string, ImportConfigRowDraft>;
};

export type ImportConfigTransactionValues = {
  /** Stable ParsedRow.id — draft identity, not submitted to the API. */
  id: string;
  /** Index among currently valid rows; used for import/AI rowIndex. */
  rowIndex: number;
  date: string;
  payee: string;
  description: string;
  amount: number;
  amountInput: string;
  /** The exact decimal to write, normalized from the bank's spelling. */
  amountDecimal: string;
  targetAccount: string;
  selected: boolean;
};

export type ImportConfigFormValues = {
  sourceAccount: string;
  defaultCurrency: string;
  transactions: ImportConfigTransactionValues[];
};

/** Rows that still pass the shared parse contract for configuration. */
export function getValidImportRows(rows: ParsedRow[]): ParsedRow[] {
  return rows.filter((row) => {
    if (row.errors && row.errors.length > 0) return false;
    return (
      parseDate(row.date).valid &&
      parseAmount(row.amountInput, { decimalComma: row.decimalComma }).valid
    );
  });
}

/**
 * Build form values from the latest valid preview rows, restoring draft
 * target/selection by ParsedRow.id and applying safe defaults for new rows.
 */
export function buildImportConfigFormValues(
  rows: ParsedRow[],
  draft: ImportConfigDraft | null | undefined,
  primaryCurrency: string,
): ImportConfigFormValues {
  const validRows = getValidImportRows(rows);
  return {
    sourceAccount: draft?.sourceAccount ?? "",
    defaultCurrency: draft?.defaultCurrency || primaryCurrency,
    transactions: validRows.map((row, index) => {
      const dateResult = parseDate(row.date);
      const amountResult = parseAmount(row.amountInput, {
        decimalComma: row.decimalComma,
      });
      const rowDraft = draft?.rows[row.id];
      return {
        id: row.id,
        rowIndex: index,
        date: dateResult.isoDate!,
        payee: row.payee,
        description: row.description,
        amount: amountResult.amount!,
        amountInput: row.amountInput,
        amountDecimal: amountResult.decimal!,
        targetAccount: rowDraft?.targetAccount ?? "",
        selected: rowDraft?.selected ?? true,
      };
    }),
  };
}

/**
 * Earlier choices for preview rows the form does not hold: a temporarily
 * invalid row keeps its target and exclusion for when it is repaired
 * (w4/309). Rows no longer in the preview are not carried.
 */
export function retainedRowChoices(
  rows: ParsedRow[],
  draft: ImportConfigDraft | null | undefined,
): Record<string, ImportConfigRowDraft> {
  const inForm = new Set(getValidImportRows(rows).map((row) => row.id));
  const kept: Record<string, ImportConfigRowDraft> = {};
  for (const row of rows) {
    const prior = draft?.rows[row.id];
    if (prior && !inForm.has(row.id)) kept[row.id] = prior;
  }
  return kept;
}

/**
 * Persist only configuration choices: the form's rows, plus `retained`
 * choices for preview rows outside it; mappings for removed rows drop out.
 */
export function toImportConfigDraft(
  values: ImportConfigFormValues,
  retained: Record<string, ImportConfigRowDraft> = {},
): ImportConfigDraft {
  const rows: Record<string, ImportConfigRowDraft> = { ...retained };
  for (const txn of values.transactions) {
    rows[txn.id] = {
      targetAccount: txn.targetAccount,
      selected: txn.selected,
    };
  }
  return {
    sourceAccount: values.sourceAccount,
    defaultCurrency: values.defaultCurrency,
    rows,
  };
}
