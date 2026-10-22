import { INSERT_INDENT } from "../../code-editor/indent-unit";
import { buildKeyboardShortcutButtons, buildPlainTextButtons } from "../utils";

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
  });
  expect(buttons[1].insert).toBe("* ");
  expect(buttons[2].insert).toBe("! ");
  expect(buttons[3]).toEqual({
    label: '""',
    insert: '""',
    cursorOffset: 1,
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
