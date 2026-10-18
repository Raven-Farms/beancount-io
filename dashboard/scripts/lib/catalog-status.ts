import {
  IDENTICAL_BY_DESIGN,
  untranslatedAgainstEnglish,
  untranslatedEnglishTail,
  untranslatedWholeMessage,
} from "../../src/test/locale-scan";
import { TODO_MARKER } from "./sync-locale";

export interface CatalogStatus {
  total: number;
  /** Keys neither marked `[TODO]` nor copied whole from English. */
  completed: number;
  percentage: number;
  todoCount: number;
  /**
   * Keys whose message still ends in verbatim English, which is what a
   * half-finished edit of a `[TODO]` line leaves behind — `Cuenta Balance`
   * from `[TODO] Account Balance`. Listed, but counted as completed.
   */
  halfTranslated: string[];
  /**
   * Keys whose message is the English one, copied whole: not translated, so
   * not completed. Brand, format and notation terms alone do not count, and
   * `IDENTICAL_BY_DESIGN` excuses a message that is correct in English.
   */
  copiedWhole: string[];
}

/**
 * How finished one locale's catalog is against English, judged by the same
 * predicates and allowlist the CI guards use (`src/test/locale-scan.ts`), so
 * the report cannot call a catalog done that CI rejects. Counting only the
 * `[TODO]` markers reported whole English copies as translated (w0/m3).
 */
export function catalogStatus(
  messages: Readonly<Record<string, string>>,
  english: Readonly<Record<string, string>>,
  locale: string,
): CatalogStatus {
  const isTodo = (key: string) => messages[key].startsWith(TODO_MARKER);
  const keysOf = (offenders: { key: string }[]) =>
    offenders.map(({ key }) => key);
  const halfTranslated = keysOf(
    untranslatedAgainstEnglish(
      messages,
      english,
      (message, source) => untranslatedEnglishTail(message, source, locale),
      isTodo,
    ),
  );
  const copiedWhole = keysOf(
    untranslatedAgainstEnglish(
      messages,
      english,
      untranslatedWholeMessage,
      (key) => isTodo(key) || `${locale}/${key}` in IDENTICAL_BY_DESIGN,
    ),
  );
  const total = Object.keys(messages).length;
  const todoCount = Object.keys(messages).filter(isTodo).length;
  const completed = total - todoCount - copiedWhole.length;
  return {
    total,
    completed,
    percentage: total > 0 ? Math.round((completed / total) * 100) : 100,
    todoCount,
    halfTranslated,
    copiedWhole,
  };
}
