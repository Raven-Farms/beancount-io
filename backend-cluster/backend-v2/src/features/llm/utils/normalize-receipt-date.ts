/**
 * A receipt date as `YYYY-MM-DD`, or null when it is not one we can read. The
 * parse schema's date is a plain string with the format only in its
 * description (a regex would break the strict response formats), so the model
 * can answer `2026/10/21`, `2026-10-21T14:32:00` or `2026-1-5`; those are
 * normalised, and a day-first or month-first form is dropped as ambiguous
 * (w21/285).
 */
export function normalizeReceiptDate(
  raw: string | null | undefined,
): string | null {
  const match = /^\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[T\s].*)?$/.exec(
    raw ?? "",
  );
  if (!match) return null;
  const [year, month, day] = [match[1]!, match[2]!, match[3]!].map(Number) as [
    number,
    number,
    number,
  ];
  const probe = new Date(Date.UTC(year, month - 1, day));
  if (
    probe.getUTCFullYear() !== year ||
    probe.getUTCMonth() !== month - 1 ||
    probe.getUTCDate() !== day
  ) {
    return null;
  }
  return [
    String(year).padStart(4, "0"),
    String(month).padStart(2, "0"),
    String(day).padStart(2, "0"),
  ].join("-");
}
