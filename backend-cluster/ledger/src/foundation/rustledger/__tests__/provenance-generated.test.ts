import type { DirectiveJson } from "@rustledger/wasm";
import {
  captureGeneratedDirectives,
  inheritDirectiveSourceId,
  isGeneratedDirective,
  markGeneratedDirective,
  restoreGeneratedDirectives,
} from "../plugins/provenance";

const directive = (narration: string) =>
  ({ type: "transaction", narration }) as unknown as DirectiveJson;

// w21/443: the mark survives a rewrite of a copy and the worker's structured clone.
describe("generated directive marks", () => {
  it("follows a rewrite of the copy, not a rewrite of its source", () => {
    const source = directive("source");
    const copy = directive("copy");
    markGeneratedDirective(copy);

    const rewrittenSource = directive("source+link");
    inheritDirectiveSourceId(source, rewrittenSource);
    expect(isGeneratedDirective(rewrittenSource)).toBe(false);

    const rewrittenCopy = directive("copy+link");
    inheritDirectiveSourceId(copy, rewrittenCopy);
    expect(isGeneratedDirective(rewrittenCopy)).toBe(true);
  });

  it("is captured in order and restored onto the cloned objects", () => {
    const copy = directive("copy");
    markGeneratedDirective(copy);
    const stream = [directive("a"), copy, directive("b")];
    const captured = captureGeneratedDirectives(stream);
    expect(captured).toEqual([false, true, false]);

    const cloned = JSON.parse(JSON.stringify(stream)) as DirectiveJson[];
    expect(cloned.map(isGeneratedDirective)).toEqual([false, false, false]);
    restoreGeneratedDirectives(cloned, captured);
    expect(cloned.map(isGeneratedDirective)).toEqual([false, true, false]);
  });
});
