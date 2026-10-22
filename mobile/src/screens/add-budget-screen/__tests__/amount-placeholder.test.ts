import fs from "fs";
import path from "path";
import { budgetAmountPlaceholder } from "../amount-placeholder";

// Update Budget's Amount showed a stock "500" that read as the budget's
// current value (w21/034).
describe("budgetAmountPlaceholder", () => {
  it("shows the budget's current amount when updating", () => {
    expect(budgetAmountPlaceholder(true, "900.50 USD")).toBe("900.50");
    // An income target is stored negative; the form asks for it positive (w21/399).
    expect(budgetAmountPlaceholder(true, "-1200 USD")).toBe("1200");
  });

  it("keeps the example when adding, or when the amount is unreadable", () => {
    expect(budgetAmountPlaceholder(false, "900.50 USD")).toBe("500");
    expect(budgetAmountPlaceholder(true, undefined)).toBe("500");
    expect(budgetAmountPlaceholder(true, "lots")).toBe("500");
  });

  it("is passed from the card and never prefilled into the field", () => {
    const read = (...parts: string[]) =>
      fs.readFileSync(path.join(__dirname, ...parts), "utf8");
    expect(
      read("..", "..", "budget-screen", "budget-screen.tsx").includes(
        "currentAmount: group.amount,",
      ),
    ).toBe(true);
    const form = read("..", "add-budget-screen.tsx");
    expect(form.includes("budgetAmountPlaceholder(")).toBe(true);
    expect(form.includes('const [amount, setAmount] = useState("");')).toBe(
      true,
    );
  });
});
