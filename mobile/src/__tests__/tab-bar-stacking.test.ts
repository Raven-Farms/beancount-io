import fs from "fs";
import path from "path";

// w21/242: both screens are pushed onto the (app) stack and then called
// `router.replace("/(app)/(tabs)")`, which in expo-router replaces the pushed
// screen with a NEW (tabs) route. Each ledger switch left another whole tab bar
// mounted underneath, with all its screens and live queries, and Android Back
// from Home landed on the old copies.
describe("opening a ledger returns to the tab bar already mounted", () => {
  const read = (...parts: string[]) =>
    fs
      .readFileSync(path.join(__dirname, "..", ...parts), "utf8")
      .replace(/\s+/g, "");

  it("pops to the existing tabs instead of replacing with a new copy", () => {
    for (const file of [
      ["screens", "ledger-selection", "index.tsx"],
      ["screens", "create-ledger-screen", "create-ledger-screen.tsx"],
    ]) {
      const source = read(...file);
      expect(source.includes('router.dismissTo("/(app)/(tabs)")')).toBe(true);
      expect(source.includes('router.replace("/(app)/(tabs)")')).toBe(false);
    }
  });
});
