import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { compileAppCss } from "@/test/tailwind";
import { beforeAll, describe, expect, it } from "vitest";
import { Combobox } from "../combobox";
import {
  Command,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "../command";

/**
 * The option Enter will apply keeps a system Highlight under forced colors,
 * following the picker's own active option (cmdk selection / Combobox
 * highlight) while focus stays in the input (w4/273), and its label stays
 * readable: the active option opts out of the text backplate that otherwise
 * hid it on that fill (w4/m43). This checks the classes on the real active
 * option and the CSS they compile to; the label pixels were measured under
 * real forced-colors rendering.
 */
const CMDK = "data-[selected=true]:forced-selected";
const COMBOBOX = "aria-selected:forced-selected";
let css = "";

beforeAll(async () => {
  css = await compileAppCss([CMDK, COMBOBOX]);
});

const active = () =>
  screen
    .getAllByRole("option")
    .filter((option) => option.getAttribute("aria-selected") === "true");

describe("active picker option under forced colors", () => {
  it("emits a Highlight fill, HighlightText and no backplate for the active option", () => {
    expect(css).toContain("forced-colors: active");
    expect(css).toMatch(/\[data-selected="true"\]/);
    expect(css).toMatch(/\[aria-selected="true"\]/);
    expect(css).toMatch(/forced-color-adjust:\s*none/);
    expect(css).toMatch(/background-color:\s*Highlight !important/);
    expect(css).toMatch(/color:\s*HighlightText !important/);
    // The ledger switcher's icon and name carry their own author colours.
    expect(css).toMatch(/& \*\s*\{[^}]*color:\s*HighlightText !important/);
  });

  it("CommandItem: the cmdk-selected row carries the forced highlight", async () => {
    const user = userEvent.setup();
    render(
      <Command label="Accounts">
        <CommandInput placeholder="Search accounts..." />
        <CommandList>
          <CommandGroup>
            {["Assets:US:BofA", "Assets:US:BofA:Checking"].map((account) => (
              <CommandItem key={account} value={account}>
                {account}
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </Command>,
    );
    await user.type(screen.getByRole("combobox"), "Assets:US:BofA");
    await user.keyboard("{ArrowDown}");
    await waitFor(() =>
      expect(active().map((o) => o.textContent)).toEqual([
        "Assets:US:BofA:Checking",
      ]),
    );
    expect(active()[0]).toHaveClass(CMDK);
  });

  it("Combobox: only the highlighted option carries the forced highlight", async () => {
    const user = userEvent.setup();
    render(
      <>
        <label htmlFor="time">Time</label>
        <Combobox
          id="time"
          options={[
            { value: "2017", label: "2017" },
            { value: "2016", label: "2016" },
          ]}
          value=""
          onValueChange={() => {}}
        />
      </>,
    );
    await user.click(screen.getByRole("combobox", { name: "Time" }));
    await user.keyboard("{ArrowDown}{ArrowDown}");
    await waitFor(() =>
      expect(active().map((o) => o.textContent)).toEqual(["2016"]),
    );
    // Keyed to the option's own state, so it follows the highlight exactly.
    for (const option of screen.getAllByRole("option")) {
      expect(option).toHaveClass(COMBOBOX);
    }
  });
});
