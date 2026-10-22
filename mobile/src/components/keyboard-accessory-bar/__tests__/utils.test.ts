import { INSERT_INDENT } from "../../code-editor/indent-unit";
import {
  buildKeyboardShortcutButtons,
  buildPlainTextButtons,
  getKeyboardOverlap,
} from "../utils";

test("keyboard shortcuts follow the transaction entry flow", () => {
  const buttons = buildKeyboardShortcutButtons("2026-07-29", ["USD"]);

  expect(buttons.map((button) => button.label)).toEqual([
    "2026-07-29",
    "*",
    "!",
    '""',
    ":",
    "USD",
    "⇥",
    "-",
    "#",
    "^",
  ]);
});

test("keyboard shortcuts preserve and deduplicate operating currencies", () => {
  const buttons = buildKeyboardShortcutButtons("2026-07-29", [
    "EUR",
    " USD ",
    "EUR",
    "",
  ]);

  const currencyButtons = buttons.slice(5, 7);
  expect(currencyButtons).toEqual([
    { label: "EUR", insert: "EUR" },
    { label: "USD", insert: "USD" },
  ]);
});

test("keyboard shortcuts omit currencies when none are configured", () => {
  const buttons = buildKeyboardShortcutButtons("2026-07-29", []);

  expect(buttons.map((button) => button.label)).toEqual([
    "2026-07-29",
    "*",
    "!",
    '""',
    ":",
    "⇥",
    "-",
    "#",
    "^",
  ]);
});

test("keyboard shortcuts insert useful multi-character syntax", () => {
  const buttons = buildKeyboardShortcutButtons("2026-07-29", []);

  expect(buttons[0]).toEqual({
    label: "2026-07-29",
    insert: "2026-07-29 ",
    isDate: true,
    spokenKey: "keyboardInsertDate",
  });
  expect(buttons[1].insert).toBe("* ");
  expect(buttons[2].insert).toBe("! ");
  expect(buttons[3]).toEqual({
    label: '""',
    insert: '""',
    cursorOffset: 1,
    spokenKey: "keyboardInsertQuotes",
  });
  // ⇥ stands for one unit of the document's indentation (w21/339).
  expect(buttons[5].insert).toBe(INSERT_INDENT);
});

// w21/339: a plain-text file's bar is ⇥ and the dismiss control; ⇥ is one unit
// of the document's own indentation.
test("a plain-text file's bar offers only the indent key", () => {
  const buttons = buildPlainTextButtons();
  expect(buttons.map((button) => button.label)).toEqual(["⇥"]);
  expect(buttons[0].insert).toBe(INSERT_INDENT);
});

// w21/562: "!", `""`, ":" and "-" are mostly not spoken at VoiceOver's default
// punctuation level, so four keys read as just "Insert, button".
describe("the shortcut keys' spoken names", () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { en } = require("../../../translations/en");
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const {
    translationLocales,
  } = require("../../../translations/__tests__/locale-parity");

  it("give every symbol key its own pronounceable name", () => {
    const buttons = buildKeyboardShortcutButtons("2026-07-29", ["USD"]);
    const symbols = buttons.filter((button) => button.label !== "USD");
    const names = symbols.map((button) => en[button.spokenKey as string]);
    expect(names.every((name) => typeof name === "string")).toBe(true);
    expect(new Set(names).size).toBe(names.length);
    // The currency code is spoken as it is.
    expect(buttons.find((button) => button.label === "USD")?.spokenKey).toBe(
      undefined,
    );
  });

  it("exist in every language", () => {
    const keys = buildKeyboardShortcutButtons("2026-07-29", [])
      .map((button) => button.spokenKey as string)
      .filter(Boolean);
    expect(keys.length).toBe(9);
    for (const locale of translationLocales()) {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const catalog = require(`../../../translations/${locale}`)[locale];
      for (const key of keys) {
        expect(typeof catalog[key]).toBe("string");
      }
    }
  });

  it("name the plain-text file's indent key too", () => {
    expect(buildPlainTextButtons()[0].spokenKey).toBe("keyboardInsertTab");
  });
});

test("the keyboard overlap subtracts the bottom inset on iOS only", () => {
  expect(getKeyboardOverlap(336, 34, "ios")).toBe(302);
  expect(getKeyboardOverlap(336, 48, "android")).toBe(336);
  expect(getKeyboardOverlap(20, 34, "ios")).toBe(0);
});
