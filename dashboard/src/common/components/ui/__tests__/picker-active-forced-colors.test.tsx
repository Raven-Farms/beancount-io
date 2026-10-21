import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { compile } from "tailwindcss";
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
 * highlight) while focus stays in the input (w4/273). This checks the
 * classes on the real active option and the CSS they compile to; pixels
 * under real forced-colors rendering were not measured here.
 */
const FORCED = [
  "forced-colors:data-[selected=true]:bg-[Highlight]",
  "forced-colors:data-[selected=true]:text-[HighlightText]",
  "forced-colors:bg-[Highlight]",
  "forced-colors:text-[HighlightText]",
];
let css = "";

beforeAll(async () => {
  const require = createRequire(`${process.cwd()}/`);
  const compiler = await compile(`@import "tailwindcss";`, {
    base: process.cwd(),
    loadStylesheet: async (id: string, base: string) => {
      const path = require.resolve(
        id === "tailwindcss" ? "tailwindcss/index.css" : id,
      );
      return { path, base, content: readFileSync(path, "utf8") };
    },
  });
  css = compiler.build(FORCED);
});

const active = () =>
  screen
    .getAllByRole("option")
    .filter((option) => option.getAttribute("aria-selected") === "true");

describe("active picker option under forced colors", () => {
  it("emits a Highlight fill and HighlightText for the active state", () => {
    expect(css).toContain("forced-colors: active");
    expect(css).toMatch(/background-color:\s*Highlight/);
    expect(css).toMatch(/color:\s*HighlightText/);
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
    expect(active()[0]!.className).toContain(
      "forced-colors:data-[selected=true]:bg-[Highlight]",
    );
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
    for (const option of screen.getAllByRole("option")) {
      expect(option.className.includes("forced-colors:bg-[Highlight]")).toBe(
        option.getAttribute("aria-selected") === "true",
      );
    }
  });
});
