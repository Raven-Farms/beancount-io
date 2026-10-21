import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { Combobox } from "../combobox";

/**
 * Accepting a suggestion keeps focus in the input, so one Tab moves on
 * instead of returning to it and reopening the list (w4/255).
 */
function Form({
  triggerOn,
  onValue,
}: {
  triggerOn: "change" | "blur";
  onValue: (value: string) => void;
}) {
  const [value, setValue] = useState("");
  return (
    <>
      <label htmlFor="account">Account</label>
      <Combobox
        id="account"
        options={[
          { value: "Assets:Cash", label: "Assets:Cash" },
          { value: "Assets:Bank", label: "Assets:Bank" },
        ]}
        value={value}
        triggerOn={triggerOn}
        onValueChange={(next) => {
          setValue(next);
          onValue(next);
        }}
      />
      <label htmlFor="next">Note content</label>
      <input id="next" />
    </>
  );
}

const account = () => screen.getByRole("combobox", { name: "Account" });

describe.each(["change", "blur"] as const)(
  "Combobox in %s mode",
  (triggerOn) => {
    it("keeps focus after a keyboard selection and Tabs on once", async () => {
      const user = userEvent.setup();
      const onValue = vi.fn();
      render(<Form triggerOn={triggerOn} onValue={onValue} />);

      await user.click(account());
      await user.type(account(), "Assets:Ca");
      await user.keyboard("{ArrowDown}{Enter}");
      expect(account()).toHaveValue("Assets:Cash");
      expect(account()).toHaveFocus();
      await waitFor(() =>
        expect(account()).toHaveAttribute("aria-expanded", "false"),
      );

      await user.tab();
      expect(
        screen.getByRole("textbox", { name: "Note content" }),
      ).toHaveFocus();
      expect(account()).toHaveAttribute("aria-expanded", "false");
      expect(onValue).toHaveBeenLastCalledWith("Assets:Cash");
      if (triggerOn === "blur") expect(onValue).toHaveBeenCalledTimes(1);
    });

    it("keeps focus after a pointer selection", async () => {
      const user = userEvent.setup();
      render(<Form triggerOn={triggerOn} onValue={vi.fn()} />);
      await user.click(account());
      await user.type(account(), "Assets:B");
      await user.click(
        await screen.findByRole("option", { name: "Assets:Bank" }),
      );
      expect(account()).toHaveValue("Assets:Bank");
      expect(account()).toHaveFocus();
    });
  },
);

it("still commits a new edit typed after a selection (blur mode)", async () => {
  const user = userEvent.setup();
  const onValue = vi.fn();
  render(<Form triggerOn="blur" onValue={onValue} />);
  await user.click(account());
  await user.type(account(), "Assets:Ca");
  await user.keyboard("{ArrowDown}{Enter}");
  await user.type(account(), ":Petty");
  await user.tab();
  expect(onValue).toHaveBeenLastCalledWith("Assets:Cash:Petty");
});
