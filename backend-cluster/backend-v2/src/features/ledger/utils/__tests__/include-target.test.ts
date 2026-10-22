import {
  formatIncludeLine,
  globMatches,
  includeTargetFor,
  parseIncludeLine,
  resolveIncludeTarget,
} from "@/features/ledger/utils/include-target";

describe("include lines", () => {
  it.each([
    ['include "x.bean"', "x.bean", '"'],
    ['  include "my file.bean"  ; note', "my file.bean", '"'],
    ['include "c\\"x.bean"', 'c"x.bean', '"'],
    ["include 'x.bean'", "x.bean", "'"],
    ["include x.bean", "x.bean", ""],
  ])("reads the target of %p", (line, target, quote) => {
    expect(parseIncludeLine(line)).toMatchObject({ target, quote });
  });

  it.each(['option "title" "x"', "; include x.bean", "include"])(
    "reads %p as no include",
    (line) => expect(parseIncludeLine(line)).toBeNull(),
  );

  it.each([
    ['include "x.bean" ; keep', "y.bean", 'include "y.bean" ; keep'],
    ['include "x.bean"', 'c"x\\y.bean', 'include "c\\"x\\\\y.bean"'],
    ["include 'x.bean'", "y.bean", "include 'y.bean'"],
    ["include x.bean", "my file.bean", 'include "my file.bean"'],
  ])("rewrites %p to name %p", (line, target, written) => {
    const rewritten = formatIncludeLine(parseIncludeLine(line)!, target);
    expect(rewritten).toBe(written);
    expect(parseIncludeLine(rewritten)?.target).toBe(target);
  });
});

describe("include targets", () => {
  it.each([
    ["main.bean", "x.bean", "x.bean"],
    ["d/inc.bean", "x.bean", "d/x.bean"],
    ["d/inc.bean", "../b.bean", "b.bean"],
    ["inc.bean", "./b.bean", "b.bean"],
    ["d/inc.bean", "/b.bean", "b.bean"],
    ["d/inc.bean", "*.bean", "d/*.bean"],
  ])("resolves %p's %p to %p", (including, target, resolved) => {
    expect(resolveIncludeTarget(including, target)).toBe(resolved);
  });

  it.each([
    ["main.bean", "c.bean", "b.bean", "c.bean"],
    ["inc3.bean", "c.bean", "./b.bean", "./c.bean"],
    ["d/inc.bean", "e/c.bean", "../b.bean", "../e/c.bean"],
    ["d/inc.bean", "d/y.bean", "./x.bean", "./y.bean"],
    ["d/inc.bean", "c.bean", "./x.bean", "../c.bean"],
    ["d/inc.bean", "e/c.bean", "/b.bean", "/e/c.bean"],
  ])(
    "names %p's new target %p in the style of %p",
    (including, path, previous, target) => {
      expect(includeTargetFor(including, path, previous)).toBe(target);
      expect(resolveIncludeTarget(including, target)).toBe(path);
    },
  );
});

describe("include globs", () => {
  it.each([
    ["d/*.bean", "d/x.bean", true],
    ["d/*.bean", "e/x.bean", false],
    ["d/*.bean", "d/sub/x.bean", false],
    ["d/*.bean", "d/.hidden.bean", false],
    ["d/.*.bean", "d/.hidden.bean", true],
    ["d/?.bean", "d/x.bean", true],
    ["d/?.bean", "d/xy.bean", false],
    ["d/[a-c].bean", "d/b.bean", true],
    ["d/[!a-c].bean", "d/b.bean", false],
    ["d/[]].bean", "d/].bean", true],
    ["d/[.bean", "d/[.bean", true],
    ["**/*.bean", "x.bean", true],
    ["**/*.bean", "a/b/x.bean", true],
    ["**/*.bean", "a/.git2/x.bean", false],
    ["d/**", "d/a/x.bean", true],
    ["d/**/x.bean", "d/x.bean", true],
  ])("%p matching %p is %p", (pattern, path, matches) => {
    expect(globMatches(pattern, path)).toBe(matches);
  });

  it("matches a long name against many stars without backtracking", () => {
    const pattern = `d/${"*a".repeat(40)}*b`;
    expect(globMatches(pattern, `d/${"a".repeat(2000)}`)).toBe(false);
  });
});
