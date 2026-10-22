import { getFormatDate } from "../../common/format-util";
import { graphQLErrorCodes } from "../../common/graphql-error-codes";

/**
 * Resolve the receipt's transaction date. The server may return an empty or
 * absent date when it can't read one off the receipt, and a value that is not
 * a real `YYYY-MM-DD` day would open the form on an Invalid Date (w21/285):
 * fall back to the client's today so the form always opens with a usable date.
 */
export const receiptDate = (date: string | null | undefined): string =>
  isIsoDay(date) ? date : getFormatDate(new Date());

const isIsoDay = (date: string | null | undefined): date is string => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date ?? "");
  if (!match) return false;
  const [year, month, day] = [match[1]!, match[2]!, match[3]!].map(Number) as [
    number,
    number,
    number,
  ];
  const probe = new Date(Date.UTC(year, month - 1, day));
  return (
    probe.getUTCFullYear() === year &&
    probe.getUTCMonth() === month - 1 &&
    probe.getUTCDate() === day
  );
};

/**
 * The parsed receipt total as the form's amount text: positive (receipts are
 * expenses, however the model signed them) and at the precision the parser
 * returned, padded to two places. `toFixed(2)` cut a KWD 12.345 to "12.35"
 * and binary-rounded 1.005 to "1.00" (w21/069).
 */
export const receiptAmountText = (amount: number): string => {
  const text = String(Math.abs(amount));
  // Exponent forms (1e-7, 1e21) are not realistic totals; keep them parseable.
  if (/e/i.test(text)) return Math.abs(amount).toFixed(2);
  const [whole, fraction = ""] = text.split(".");
  return `${whole}.${fraction.padEnd(2, "0")}`;
};

/**
 * Map an internal error code to a translation key.
 *
 * Only covers the capture → upload → parse leg; saving happens later on the
 * transaction form, which reports its own errors.
 */
export const receiptErrorKey = (
  code: string,
): "receiptQuotaExhausted" | "receiptParseFailed" | "receiptUploadFailed" => {
  if (code === "quota_exhausted") return "receiptQuotaExhausted";
  if (code === "parse_failed") return "receiptParseFailed";
  return "receiptUploadFailed";
};

/**
 * Whether trying the same photo again can help. A spent AI quota stays spent;
 * a dropped connection or an unreadable parse does not (w21/204).
 */
export const receiptCanRetry = (code: string): boolean =>
  code !== "quota_exhausted";

/**
 * Classify a failure thrown by the parse-leg mutation into an internal code.
 *
 * Under Apollo's default errorPolicy a GraphQL error rejects the promise
 * rather than populating `result.errors`, so the leg is classified here from
 * the thrown `ApolloError`'s `graphQLErrors[].extensions.code`. The backend
 * raises `RESOURCE_LIMIT_REACHED` when the AI quota is spent (ADR 0011);
 * everything else on this leg is a parse failure. A network error carries no
 * GraphQL codes and falls through to `parse_failed` — the upload already
 * succeeded, so it is not an upload failure.
 */
export const parseErrorCode = (
  err: unknown,
): "quota_exhausted" | "parse_failed" => {
  const codes = graphQLErrorCodes(err);
  if (codes.includes("RESOURCE_LIMIT_REACHED")) return "quota_exhausted";
  return "parse_failed";
};

/** Derive file extension from a MIME type, falling back to jpg. */
export const mimeToExt = (mimeType: string): string =>
  mimeType.split("/")[1] ?? "jpg";

/** The shape of `launchImageLibraryAsync`'s result this screen depends on. */
export type LibraryPickResult = {
  canceled: boolean;
  assets?:
    | ({
        uri: string;
        mimeType?: string | null;
        fileName?: string | null;
      } | null)[]
    | null;
};

/** What a picked receipt hands to the preview (mirrors `CapturedShot`). */
export type PickedShot = {
  uri: string;
  mimeType: string;
  filename: string;
};

/**
 * Normalize one library pick into a shot, or `null` when there is nothing to
 * use (the user cancelled, or the picker returned no asset).
 *
 * Pure so the library-pick path can be unit-tested without a picker: the screen
 * passes whatever `ImagePicker.launchImageLibraryAsync` resolved to straight in.
 */
export const shotFromLibraryResult = (
  result: LibraryPickResult | null | undefined,
): PickedShot | null => {
  const asset = result && !result.canceled ? result.assets?.[0] : null;
  if (!asset?.uri) {
    return null;
  }
  const reported = asset.mimeType ?? "image/jpeg";
  // The file the picker returned says what it is: on Android it re-encodes a
  // HEIC photo into a `.jpeg` cache file yet still reports `image/heic` and
  // the `.heic` name, which the server then refuses (w21/282). Fall back to
  // the reported type only when the extension says nothing.
  const fileType = typeOfExtension(extensionOf(asset.uri));
  const mimeType = fileType ?? reported;
  const nameType = asset.fileName
    ? typeOfExtension(extensionOf(asset.fileName))
    : null;
  const filename =
    asset.fileName && (fileType === null || nameType === fileType)
      ? asset.fileName
      : `${stem(asset.fileName)}.${fileType ? extensionOf(asset.uri) : mimeToExt(mimeType)}`;
  return { uri: asset.uri, mimeType, filename };
};

const EXTENSION_TYPES: Record<string, string> = {
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
  gif: "image/gif",
};

/** The lower-cased extension of a path or URI, without query or fragment. */
const extensionOf = (path: string): string => {
  const name = path.split(/[?#]/u)[0]!.split("/").pop() ?? "";
  const dot = name.lastIndexOf(".");
  return dot < 0 ? "" : name.slice(dot + 1).toLowerCase();
};

const typeOfExtension = (extension: string): string | null =>
  EXTENSION_TYPES[extension] ?? null;

/** A file name without its extension, or `receipt` when there is none. */
const stem = (fileName: string | null | undefined): string => {
  const dot = fileName ? fileName.lastIndexOf(".") : -1;
  const base = fileName && dot > 0 ? fileName.slice(0, dot) : (fileName ?? "");
  return base || "receipt";
};
