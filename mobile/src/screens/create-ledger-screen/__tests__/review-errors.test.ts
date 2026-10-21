import fs from "fs";
import path from "path";

// w21/105: on Review, a name conflict or an invalid opening amount stopped the
// spinner and showed nothing, because both errors render on the form step.
describe("Create Ledger's Review step", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "create-ledger-screen.tsx"),
    "utf8",
  );

  it("validates every form field before leaving the form step", () => {
    expect(
      source.includes("if (step === 1 && !(await trigger())) return;"),
    ).toBe(true);
    expect(source.includes('trigger("name")')).toBe(false);
  });

  it("returns to the form step on a refused name or an invalid field", () => {
    const conflict = source.indexOf(
      'setError("name", { message: t("createLedgerNameConflict") });',
    );
    expect(conflict > 0).toBe(true);
    expect(
      source.slice(conflict, conflict + 200).includes("setStep(FORM_STEP);"),
    ).toBe(true);
    expect(source.includes("    () => setStep(FORM_STEP),")).toBe(true);
    expect(source.includes("const FORM_STEP = 1;")).toBe(true);
  });
});
