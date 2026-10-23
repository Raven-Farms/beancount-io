import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { BudgetFilterPills } from "../budget-filter-pills";

/**
 * The selected pill's fill, ring and shadow disappear in forced colors, so
 * All and Monthly painted alike (w4/m43). Each pill carries `forced-selected`
 * behind its own pressed state; the paint was measured in a real browser.
 */
function Harness() {
  const [value, setValue] = useState("all");
  return (
    <BudgetFilterPills
      label="Interval"
      options={[
        { value: "all", label: "All" },
        { value: "monthly", label: "Monthly" },
      ]}
      value={value}
      onChange={setValue}
    />
  );
}

const pressed = () =>
  screen.getAllByRole("button").filter((pill) => {
    expect(pill).toHaveClass("aria-pressed:forced-selected");
    return pill.getAttribute("aria-pressed") === "true";
  });

describe("Budget filter pills under forced colors", () => {
  it("gates the highlight on the pressed pill, which follows the selection", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    expect(pressed().map((pill) => pill.textContent)).toEqual(["All"]);

    await user.click(screen.getByRole("button", { name: "Monthly" }));
    expect(pressed().map((pill) => pill.textContent)).toEqual(["Monthly"]);
  });
});
