import { useState, useCallback } from "react";
import { useTranslations } from "@/common/hooks/use-translations";
import type { ParsedRow, CSVParseResult } from "../types";
import {
  isValidRowFormat,
  detectHeaderRow,
  buildParsedRow,
  createParsedRowId,
  resolveDecimalConvention,
  type ImportColumnField,
} from "../utils/csv-validator";

const UNSUPPORTED_LAYOUT_ERROR =
  "Unsupported CSV columns. Expected exactly Date, Payee, Description (or Narration), and Amount — in any order.";

type ParseRecordsResult =
  | { ok: true; records: string[][] }
  | { ok: false; error: string };

const DELIMITERS = [",", ";", "\t"] as const;

/** The first record's text, up to the first newline outside quotes. */
function firstRecordText(text: string): string {
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '"') inQuotes = !inQuotes;
    else if (!inQuotes && (text[i] === "\n" || text[i] === "\r")) {
      return text.slice(0, i);
    }
  }
  return text;
}

/**
 * The field separator a bank export uses. Most European banks write `;`
 * (their decimal mark is the comma), some exports use tabs. A recognized
 * header decides it; otherwise the delimiter that splits the first record
 * into the four import columns; otherwise a comma.
 */
function detectDelimiter(text: string): string {
  const first = firstRecordText(text);
  const split = (delimiter: string) => {
    const parsed = parseRecords(first, delimiter);
    return parsed.ok ? (parsed.records[0] ?? []) : [];
  };
  for (const delimiter of DELIMITERS) {
    const header = detectHeaderRow(split(delimiter));
    if (header.isHeader && header.supported) return delimiter;
  }
  const fourColumns = DELIMITERS.filter(
    (delimiter) => split(delimiter).length === 4,
  );
  return fourColumns.length === 1 ? fourColumns[0] : ",";
}

/**
 * Parse logical CSV records from the full input, carrying quote state across
 * physical line endings (RFC 4180). Newlines separate records only outside
 * quotes; CRLF inside a quoted field is preserved as a single `\n`. The field
 * delimiter (`,`, `;` or tab) is detected from the first record.
 */
export function parseCSVRecords(content: string): ParseRecordsResult {
  const text = content.replace(/^\uFEFF/, "");
  return parseRecords(text, detectDelimiter(text));
}

function parseRecords(text: string, delimiter: string): ParseRecordsResult {
  const records: string[][] = [];
  let columns: string[] = [];
  let currentField = "";
  let inQuotes = false;
  let i = 0;

  const pushRecord = () => {
    columns.push(currentField.trim());
    currentField = "";
    // Skip blank physical lines (a single empty field after trim).
    if (!(columns.length === 1 && columns[0] === "")) {
      records.push(columns);
    }
    columns = [];
  };

  while (i < text.length) {
    const char = text[i];

    if (inQuotes) {
      if (char === '"') {
        // RFC 4180: "" inside a quoted field is one literal ".
        if (i + 1 < text.length && text[i + 1] === '"') {
          currentField += '"';
          i += 2;
          continue;
        }
        inQuotes = false;
        i += 1;
        continue;
      }
      if (char === "\r") {
        currentField += "\n";
        i += text[i + 1] === "\n" ? 2 : 1;
        continue;
      }
      currentField += char;
      i += 1;
      continue;
    }

    if (char === '"') {
      inQuotes = true;
      i += 1;
      continue;
    }
    if (char === delimiter) {
      columns.push(currentField.trim());
      currentField = "";
      i += 1;
      continue;
    }
    if (char === "\r" || char === "\n") {
      i += char === "\r" && text[i + 1] === "\n" ? 2 : 1;
      pushRecord();
      continue;
    }

    currentField += char;
    i += 1;
  }

  if (inQuotes) {
    return {
      ok: false,
      error: "Unterminated quoted field in CSV",
    };
  }

  // Final record when the file does not end with a newline.
  if (currentField.length > 0 || columns.length > 0) {
    pushRecord();
  }

  return { ok: true, records };
}

/** A whole-file failure: one diagnostic row, nothing importable. */
function fileLevelFailure(error: string): CSVParseResult {
  return {
    rows: [
      {
        id: createParsedRowId(),
        date: "",
        payee: "",
        description: "",
        amount: 0,
        amountInput: "",
        errors: [error],
      },
    ],
    validCount: 0,
    errorCount: 1,
    hasErrors: true,
  };
}

/**
 * Read a 4-column data record into import fields.
 *
 * With a header, values are taken by the column name the file declared, so a
 * `Date,Payee,Amount,Description` export keeps its amount in `amount` instead
 * of silently swapping in the description. Headerless files keep the documented
 * canonical order.
 */
function readRecordFields(
  columns: string[],
  fields: (ImportColumnField | null)[] | null,
): { date: string; payee: string; description: string; amountInput: string } {
  if (!fields) {
    const [date = "", payee = "", description = "", amountInput = ""] = columns;
    return { date, payee, description, amountInput };
  }

  const valueOf = (field: ImportColumnField) =>
    columns[fields.indexOf(field)] ?? "";

  return {
    date: valueOf("date"),
    payee: valueOf("payee"),
    description: valueOf("description"),
    amountInput: valueOf("amount"),
  };
}

/**
 * Hook for parsing CSV files
 */
export function useCSVParser() {
  const { t } = useTranslations();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Parse CSV content string
   */
  const parseCSV = useCallback((content: string): CSVParseResult => {
    const parsed = parseCSVRecords(content);

    if (!parsed.ok) {
      return fileLevelFailure(parsed.error);
    }

    const { records } = parsed;
    if (records.length === 0) {
      return {
        rows: [],
        validCount: 0,
        errorCount: 0,
        hasErrors: false,
      };
    }

    const header = detectHeaderRow(records[0]);
    // A header we recognize but cannot map must fail loudly: guessing a
    // position would emit plausible-but-wrong amounts.
    if (header.isHeader && !header.supported) {
      return fileLevelFailure(UNSUPPORTED_LAYOUT_ERROR);
    }

    const hasHeader = header.isHeader;
    const columnFields = hasHeader ? header.fields : null;
    const dataRecords = hasHeader ? records.slice(1) : records;

    // One decimal mark per amount column, decided from every cell (w0/007).
    const convention = resolveDecimalConvention(
      dataRecords
        .filter(isValidRowFormat)
        .map((columns) => readRecordFields(columns, columnFields).amountInput),
    );

    const rows: ParsedRow[] = dataRecords.map((columns, idx) => {
      const errors: string[] = [];
      const rowNum = idx + (hasHeader ? 2 : 1);

      if (!isValidRowFormat(columns)) {
        errors.push(
          `Row ${rowNum}: Expected 4 columns (Date, Payee, Description, Amount), got ${columns.length}`,
        );
        const fields = readRecordFields(columns, columnFields);
        return {
          id: createParsedRowId(),
          date: fields.date || "",
          payee: fields.payee || "",
          description: fields.description || "",
          amount: 0,
          amountInput: fields.amountInput || "",
          errors,
        };
      }

      return buildParsedRow(readRecordFields(columns, columnFields), {
        decimalComma: convention.decimalComma,
        decimalMixed: convention.mixed,
      });
    });

    const errorCount = rows.filter(
      (row) => row.errors && row.errors.length > 0,
    ).length;
    const validCount = rows.length - errorCount;
    const hasUnsupportedPrecision = rows.some(
      (row) => row.amountFailureReason === "unsupported-precision",
    );

    return {
      rows,
      validCount,
      errorCount,
      hasErrors: errorCount > 0,
      blockLlmFallback: hasUnsupportedPrecision
        ? "unsupported-precision"
        : undefined,
    };
  }, []);

  /**
   * Parse CSV file
   */
  const parseFile = useCallback(
    (file: File): Promise<CSVParseResult> => {
      return new Promise((resolve, reject) => {
        setIsLoading(true);
        setError(null);

        const reader = new FileReader();

        reader.onload = (e) => {
          try {
            const content = e.target?.result as string;
            const result = parseCSV(content);
            setIsLoading(false);
            resolve(result);
          } catch (err) {
            console.error("Failed to parse CSV:", err);
            const errorMessage = t("importer.error.failedToParse");
            setError(errorMessage);
            setIsLoading(false);
            reject(new Error(errorMessage));
          }
        };

        reader.onerror = () => {
          const errorMessage = t("importer.error.failedToParse");
          setError(errorMessage);
          setIsLoading(false);
          reject(new Error(errorMessage));
        };

        reader.readAsText(file);
      });
    },
    [parseCSV, t],
  );

  return {
    parseFile,
    parseCSV,
    isLoading,
    error,
  };
}
