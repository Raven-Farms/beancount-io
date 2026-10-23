import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import { compileAppCss, parseRules } from "@/test/tailwind";
import { Tabs, TabsList, TabsTrigger } from "../tabs";

/**
 * Forced colors replaces every author colour with the user's palette, so the
 * default variant's background-plus-shadow cue and the underline variant's
 * border colour both stopped distinguishing anything: every tab rendered the
 * same, and the selected one was unidentifiable once focus moved away.
 *
 * A class-name assertion would not show that, so these cases run the classes
 * the components actually render through Tailwind and assert on the CSS it
 * emits — that a `forced-colors: active` block exists and that the selected
 * tab resolves differently from an unselected one inside it. The rendered
 * geometry itself was measured in a real browser under forced-colors
 * emulation.
 */

let selectedPill = "";
let unselectedPill = "";
let selectedUnderline = "";
let unselectedUnderline = "";

/** The rule body Tailwind emitted for one utility class. */
let ruleFor: (className: string) => string;
/** The whole sheet, for assertions that span several utilities. */
let sheet = "";

beforeAll(async () => {
  render(
    <>
      <Tabs value="a">
        <TabsList variant="default">
          <TabsTrigger value="a">Selected</TabsTrigger>
          <TabsTrigger value="b">Other</TabsTrigger>
        </TabsList>
      </Tabs>
      <Tabs value="c">
        <TabsList variant="underline">
          <TabsTrigger value="c">Underlined</TabsTrigger>
          <TabsTrigger value="d">Plain</TabsTrigger>
        </TabsList>
      </Tabs>
    </>,
  );

  selectedPill = screen.getByText("Selected").className;
  unselectedPill = screen.getByText("Other").className;
  selectedUnderline = screen.getByText("Underlined").className;
  unselectedUnderline = screen.getByText("Plain").className;

  const every = [
    selectedPill,
    unselectedPill,
    selectedUnderline,
    unselectedUnderline,
  ]
    .join(" ")
    .split(/\s+/)
    .filter(Boolean);
  sheet = await compileAppCss(every);
  const rules = parseRules(sheet);
  ruleFor = (className: string) => rules.get(className) ?? "";
});

/**
 * Both triggers render the same class list — only `data-state` differs at
 * runtime — so what matters is whether a declaration is scoped to the selected
 * state.
 */
function declarations(classes: string) {
  return classes
    .split(/\s+/)
    .filter((name) => ruleFor(name).includes("forced-colors: active"))
    .map((name) => {
      const css = ruleFor(name);
      return {
        name,
        css,
        onlyWhenSelected: /\[data-state\s*=\s*"?active"?\]/.test(css),
      };
    });
}

const matching = (classes: string, property: RegExp) =>
  declarations(classes).filter((rule) => property.test(rule.css));

/** Declarations that only apply under forced colors, across a class list. */
function forcedColorsCss(classes: string): string {
  const blocks = declarations(classes)
    .map((rule) => rule.css)
    .filter((css) => css.includes("forced-colors: active"));
  expect(blocks.length).toBeGreaterThan(0);
  return blocks.join("\n");
}

describe("pill tabs under forced colors", () => {
  it("claims the highlight colour, and only when selected", () => {
    const fills = matching(selectedPill, /background-color:\s*Highlight/);

    expect(fills.length).toBeGreaterThan(0);
    expect(fills.every((rule) => rule.onlyWhenSelected)).toBe(true);
    expect(
      matching(selectedPill, /color:\s*HighlightText/).every(
        (rule) => rule.onlyWhenSelected,
      ),
    ).toBe(true);
  });

  it("keeps the selected label readable, and only the selected one", () => {
    // Forced colors paints a Canvas plate behind text, which hid the selected
    // pill's label on its Highlight fill (w4/m43). The opt-out is scoped to
    // the selected tab, and its colours are important so the dark theme's
    // more specific active fill cannot return once adjustment is off.
    const optOut = matching(selectedPill, /forced-color-adjust:\s*none/);

    expect(optOut.length).toBe(1);
    expect(optOut[0]!.onlyWhenSelected).toBe(true);
    expect(
      matching(selectedPill, /background-color:\s*Highlight !important/).length,
    ).toBeGreaterThan(0);
    expect(matching(selectedUnderline, /forced-color-adjust/).length).toBe(0);
  });

  it("hides the otherwise-transparent border on every tab", () => {
    // Forced colors makes `border-transparent` visible, which is what gave
    // every tab an identical outline.
    const hidden = matching(selectedPill, /border-color:\s*Canvas\b/);

    expect(hidden.length).toBeGreaterThan(0);
    expect(hidden.some((rule) => !rule.onlyWhenSelected)).toBe(true);
  });

  it("emits a forced-colors block at all", () => {
    expect(forcedColorsCss(selectedPill)).toMatch(/Highlight|Canvas/);
  });
});

describe("underline tabs under forced colors", () => {
  it("underlines only the selected tab", () => {
    const underline = matching(
      selectedUnderline,
      /border-bottom-color:\s*Highlight/,
    );

    expect(underline.length).toBeGreaterThan(0);
    expect(underline.every((rule) => rule.onlyWhenSelected)).toBe(true);
  });

  it("sinks every other underline into the background", () => {
    const hidden = matching(
      unselectedUnderline,
      /border-bottom-color:\s*Canvas\b/,
    );

    expect(hidden.length).toBeGreaterThan(0);
    expect(hidden.some((rule) => !rule.onlyWhenSelected)).toBe(true);
  });
});

describe("keyboard focus stays separately visible", () => {
  it("draws a real outline, since the focus ring is a dropped shadow", () => {
    for (const classes of [selectedPill, selectedUnderline]) {
      const css = forcedColorsCss(classes);
      expect(css).toMatch(/outline-style:\s*solid/);
      expect(css).toMatch(/outline-color:\s*CanvasText/);
    }
  });

  it("uses a different colour from the selection marker", () => {
    // CanvasText outline against a Highlight fill — two separate cues.
    const css = forcedColorsCss(selectedPill);
    expect(css).toMatch(/outline-color:\s*CanvasText/);
    expect(css).toMatch(/background-color:\s*Highlight/);
  });
});

describe("ordinary colours are untouched", () => {
  it("keeps the normal selected-pill background and shadow", () => {
    const shadow = ruleFor("data-[state=active]:shadow-sm");

    expect(shadow).toMatch(/--tw-shadow|box-shadow/);
    // The ordinary cue is unconditional; nothing was moved behind the query.
    expect(shadow).not.toContain("forced-colors: active");
    expect(sheet).toContain("forced-colors: active");
  });
});
