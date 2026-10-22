import { INSERT_INDENT } from "../code-editor/indent-unit";

export type KeyboardShortcutButton = {
  label: string;
  insert: string;
  cursorOffset?: number;
  isDate?: boolean;
  /**
   * The translation key of what VoiceOver says for the key. The symbols "!",
   * `""`, ":" and "-" are mostly not spoken, so four keys read as just "Insert"
   * (w21/562); a currency code is pronounceable and has none.
   */
  spokenKey?: string;
};

/**
 * Keyboard events report height from the bottom of the window, while the
 * editor is laid out above its bottom safe-area inset. Convert the event
 * height into the portion that actually overlaps the editor.
 */
export function getKeyboardOverlap(
  keyboardHeight: number,
  bottomInset: number,
): number {
  return Math.max(0, keyboardHeight - bottomInset);
}

export function buildKeyboardShortcutButtons(
  today: string,
  operatingCurrencies: string[],
): KeyboardShortcutButton[] {
  const currencyButtons = Array.from(
    new Set(
      operatingCurrencies
        .map((currency) => currency.trim())
        .filter((currency) => currency.length > 0),
    ),
  ).map((currency) => ({ label: currency, insert: currency }));

  return [
    {
      label: today,
      insert: `${today} `,
      isDate: true,
      spokenKey: "keyboardInsertDate",
    },
    { label: "*", insert: "* ", spokenKey: "keyboardInsertCleared" },
    { label: "!", insert: "! ", spokenKey: "keyboardInsertPending" },
    {
      label: '""',
      insert: '""',
      cursorOffset: 1,
      spokenKey: "keyboardInsertQuotes",
    },
    { label: ":", insert: ":", spokenKey: "keyboardInsertColon" },
    ...currencyButtons,
    { label: "⇥", insert: INSERT_INDENT, spokenKey: "keyboardInsertTab" },
    { label: "-", insert: "-", spokenKey: "keyboardInsertMinus" },
    { label: "#", insert: "#", spokenKey: "keyboardInsertTag" },
    { label: "^", insert: "^", spokenKey: "keyboardInsertLink" },
  ];
}

/**
 * The bar of a file that is not Beancount: just ⇥, since a hardware Tab is the
 * only other way to indent and a touch keyboard has none (w21/339).
 */
export function buildPlainTextButtons(): KeyboardShortcutButton[] {
  return [
    { label: "⇥", insert: INSERT_INDENT, spokenKey: "keyboardInsertTab" },
  ];
}
