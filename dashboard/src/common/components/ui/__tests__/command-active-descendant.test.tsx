import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "../command";

/**
 * The input always names the option cmdk shows as selected — the one Enter
 * opens — including after typing narrows the list to a single row
 * (dip/cmdk#413; w4/252).
 */
const ACCOUNTS = [
  "Assets",
  "Assets:US",
  "Assets:US:BofA",
  "Assets:US:BofA:Checking",
  "Assets:US:BofA:Savings",
  "Expenses",
  "Expenses:Food",
];

function Picker() {
  return (
    <Command label="Search accounts">
      <CommandInput placeholder="Search accounts..." />
      <CommandList>
        <CommandEmpty>No accounts found</CommandEmpty>
        <CommandGroup>
          {ACCOUNTS.map((account) => (
            <CommandItem key={account} value={account}>
              {account}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </Command>
  );
}

async function expectAligned() {
  const input = screen.getByRole("combobox");
  await waitFor(() => {
    const selected = screen
      .getAllByRole("option")
      .find((option) => option.getAttribute("aria-selected") === "true");
    expect(selected).toBeDefined();
    expect(input).toHaveAttribute("aria-activedescendant", selected!.id);
  });
}

describe("Command active descendant", () => {
  it("names the single remaining option after sequential typing", async () => {
    const user = userEvent.setup();
    render(<Picker />);
    await user.type(screen.getByRole("combobox"), "Assets:US:BofA:Checking");
    await waitFor(() => expect(screen.getAllByRole("option")).toHaveLength(1));
    await expectAligned();

    await user.keyboard("{ArrowDown}");
    await expectAligned();
  });

  it("follows arrow movement across several results", async () => {
    const user = userEvent.setup();
    render(<Picker />);
    await user.type(screen.getByRole("combobox"), "Assets:US:BofA");
    await expectAligned();
    await user.keyboard("{ArrowDown}");
    await expectAligned();
  });

  it("drops the reference when nothing matches", async () => {
    const user = userEvent.setup();
    render(<Picker />);
    await user.type(screen.getByRole("combobox"), "zzz-no-match");
    await waitFor(() =>
      expect(screen.getByRole("combobox")).not.toHaveAttribute(
        "aria-activedescendant",
      ),
    );
  });
});
