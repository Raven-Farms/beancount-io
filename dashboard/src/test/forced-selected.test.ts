import { beforeAll, describe, expect, it } from "vitest";
import { compileAppCss, parseRules } from "./tailwind";

/**
 * A selected control in forced colors kept its Highlight fill, but the
 * browser painted a Canvas backplate behind its label, which hid the text as
 * a solid block (w4/m43). `forced-selected` in style.css is the repair; these
 * cases assert the CSS it compiles to, and that each control's variant keys it
 * to that control's own selected state. The label pixels were measured under
 * real forced-colors rendering.
 */
const GATES: Record<string, RegExp> = {
  "aria-pressed:forced-selected": /\[aria-pressed="true"\]/,
  "aria-selected:forced-selected": /\[aria-selected="true"\]/,
  "data-[selected=true]:forced-selected": /\[data-selected="true"\]/,
  "data-[state=active]:forced-selected": /\[data-state="active"\]/,
  "data-[selected-single=true]:forced-selected":
    /\[data-selected-single="true"\]/,
  "has-[:checked]:forced-selected": /:has\(\*:is\(:checked\)\)/,
};

let rules: Map<string, string>;
const utility = () => rules.get("forced-selected") ?? "";

beforeAll(async () => {
  rules = parseRules(
    await compileAppCss(["forced-selected", ...Object.keys(GATES)]),
  );
});

describe("forced-selected", () => {
  it("applies only under forced colors and opts the label out of the backplate", () => {
    expect(utility()).toMatch(/^\s*@media \(forced-colors: active\) \{/);
    expect(utility()).toMatch(/forced-color-adjust:\s*none/);
  });

  it("keeps the user's system pair, over dark and hover author colours", () => {
    // `dark` adds a class's specificity, so a plain forced-colors rule lost to
    // a selected pill's dark fill once adjustment was off.
    expect(utility()).toMatch(/background-color:\s*Highlight !important/);
    expect(utility()).toMatch(/(?<!-)color:\s*HighlightText !important/);
    expect(utility()).toMatch(/border-color:\s*Highlight !important/);
  });

  it("paints like forced colors would: no shadow, no author fill below it", () => {
    expect(utility()).toMatch(/box-shadow:\s*none !important/);
    expect(utility()).toMatch(
      /& \*\s*\{\s*background-color:\s*transparent !important;\s*color:\s*HighlightText !important/,
    );
  });

  it.each(Object.entries(GATES))(
    "%s applies only in that selected state",
    (name, gate) => {
      const css = rules.get(name) ?? "";
      expect(css).toMatch(gate);
      expect(css).toMatch(/forced-color-adjust:\s*none/);
    },
  );
});
