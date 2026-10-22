import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { compile } from "tailwindcss";

/**
 * Compile class names against the app's own stylesheet, so its custom
 * variants and utilities (`dark`, `forced-selected`) resolve as they do in the
 * build. For tests that assert on the CSS a component's classes emit, which a
 * class-name check alone cannot show.
 */
export async function compileAppCss(classes: string[]): Promise<string> {
  const require = createRequire(`${process.cwd()}/`);
  const path = resolve("src/style.css");
  const compiler = await compile(readFileSync(path, "utf8"), {
    base: dirname(path),
    loadStylesheet: async (id, base) => {
      // tw-animate-css exposes a CSS-only `style` export, not a Node main.
      const imported =
        id === "tw-animate-css"
          ? resolve("node_modules/tw-animate-css/dist/tw-animate.css")
          : id.startsWith(".")
            ? resolve(base, id)
            : require.resolve(
                id === "tailwindcss" ? "tailwindcss/index.css" : id,
                { paths: [base] },
              );
      return {
        path: imported,
        base: dirname(imported),
        content: readFileSync(imported, "utf8"),
      };
    },
  });
  return compiler.build([...new Set(classes)]);
}

/**
 * Split a Tailwind sheet into `class name -> rule body`. `compiler.build` is
 * incremental and returns the accumulated sheet, so compile every class in
 * one pass and look them up here.
 */
export function parseRules(css: string): Map<string, string> {
  const rules = new Map<string, string>();
  const selector = /\.((?:[^\s{},\\]|\\.)+)\s*\{/g;
  let match: RegExpExecArray | null;
  while ((match = selector.exec(css)) !== null) {
    let depth = 1;
    let i = selector.lastIndex;
    for (; i < css.length && depth > 0; i++) {
      if (css[i] === "{") depth++;
      else if (css[i] === "}") depth--;
    }
    rules.set(
      match[1].replace(/\\/g, ""),
      css.slice(selector.lastIndex, i - 1),
    );
  }
  return rules;
}
