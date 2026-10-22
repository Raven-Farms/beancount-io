import fs from "fs";
import path from "path";

// w21/609: "numbers-and-punctuation" is iOS-only; React Native's Android
// mapping has no case for it, so the amount opened a full letter keyboard.
const screen = fs
  .readFileSync(path.join(__dirname, "..", "add-budget-screen.tsx"), "utf8")
  .replace(/\s+/g, "");

test("the budget amount asks Android for a numeric keypad", () => {
  expect(
    screen.includes(
      'keyboardType={Platform.OS==="ios"?"numbers-and-punctuation":"numeric"}',
    ),
  ).toBe(true);
  expect(screen.includes('keyboardType="numbers-and-punctuation"')).toBe(false);
});
