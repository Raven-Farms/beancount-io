import type { ColorTheme } from "@/types/theme-props";
import { sameLedgerFile } from "../../common/ledger-file-path";

type FileError = {
  message: string;
  lineno?: number | null;
  filename?: string | null;
};

/**
 * Whether a message names this file. A path in the message must be this
 * file's whole path, so `2023/x.bean` is not `2024/x.bean` (w21/089); a bare
 * filename is all the message says, and still counts.
 */
function messageNamesFile(message: string, filePath: string): boolean {
  const fileName = filePath.split("/").pop() ?? filePath;
  let from = message.indexOf(fileName);
  while (from >= 0) {
    const start = message.slice(0, from).search(/\S*$/);
    const named = message.slice(start, from + fileName.length);
    if (named === fileName || sameLedgerFile(named, filePath)) return true;
    from = message.indexOf(fileName, from + 1);
  }
  return false;
}

export function filterFileErrors(
  allErrors: FileError[],
  filePath: string,
): FileError[] {
  return allErrors.filter((e) => {
    if (e.filename != null && e.filename !== "") {
      return sameLedgerFile(e.filename, filePath);
    }
    // `getLedgerErrors` can return a null filename and name the file in the
    // message instead ("parse errors in main.bean"). Verified against a live
    // ledger: without this fallback the banner matched nothing and never
    // rendered for any file, however broken the ledger was.
    return (
      typeof e.message === "string" && messageNamesFile(e.message, filePath)
    );
  });
}

/**
 * Colors for the read-only notice. It is an explanatory sentence, not a
 * disabled control, so it uses the secondary-text role (`black80`) rather than
 * the placeholder/disabled ramp: light `black60` on the `black10` inset band
 * measured 1.62:1, unreadable at 13pt.
 */
export function readOnlyNoticeColors(theme: ColorTheme): {
  background: string;
  foreground: string;
} {
  return { background: theme.black10, foreground: theme.black80 };
}
