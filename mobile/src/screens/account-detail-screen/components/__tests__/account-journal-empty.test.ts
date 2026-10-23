import fs from "fs";
import path from "path";
import vm from "vm";
import ts from "typescript";
import * as dynamicType from "../../../../common/theme/dynamic-type";

// Executes the real account-journal empty state. The first load used to be a
// bare centered spinner under "Transactions" (w21/005); it is now skeleton
// rows shaped like the journal, restacked at accessibility sizes the way
// AccountEntryRow is.
type Node = { type: unknown; props: Record<string, any>; children: unknown[] };

let fontScale = 1;
const react = {
  createElement: (type: unknown, props: any, ...children: unknown[]): Node => ({
    type,
    props: props ?? {},
    children: children
      .flat()
      .filter((child) => child != null && child !== false && child !== ""),
  }),
};

function load(): Record<string, (props: Record<string, unknown>) => Node> {
  const exports: Record<string, any> = {};
  const source = ts.transpileModule(
    fs.readFileSync(
      path.join(__dirname, "..", "account-journal-empty.tsx"),
      "utf8",
    ),
    {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        jsx: ts.JsxEmit.React,
      },
    },
  ).outputText;
  const modules: Record<string, unknown> = {
    "react-native": {
      StyleSheet: { create: (styles: unknown) => styles },
      Text: "Text",
      View: "View",
      useWindowDimensions: () => ({ fontScale }),
    },
    "@/common/theme": {
      fontSizes: {},
      gutter: 16,
      sectionHeaderPaddingVertical: 6,
      prefersStackedLayout: dynamicType.prefersStackedLayout,
    },
    "@/common/hooks/use-theme-style": { useThemeStyle: (fn: any) => fn({}) },
    "@/components/crossfade": { FadeOutView: "FadeOutView" },
    "@/components/loading-tile": { LoadingTile: "LoadingTile" },
  };
  vm.runInNewContext(source, {
    exports,
    React: react,
    require: (id: string) => modules[id],
  });
  return exports;
}

function findAll(node: unknown, match: (node: Node) => boolean): Node[] {
  if (!node || typeof node !== "object") return [];
  const element = node as Node;
  return (match(element) ? [element] : []).concat(
    ...element.children.map((child) => findAll(child, match)),
  );
}
const flat = (style: unknown): Record<string, unknown> =>
  Array.isArray(style)
    ? Object.assign({}, ...style.map(flat))
    : style && typeof style === "object"
      ? (style as Record<string, unknown>)
      : {};

const { AccountJournalListEmpty } = load();
// The skeleton is the component the first-load branch renders.
const AccountJournalSkeleton = AccountJournalListEmpty({
  loading: true,
  message: "",
}).type as (props: Record<string, unknown>) => Node;

describe("AccountJournalListEmpty", () => {
  it("shows skeleton rows, not a spinner, on the first load", () => {
    const empty = AccountJournalListEmpty({ loading: true, message: "x" });
    expect((empty.type as { name: string }).name).toBe(
      "AccountJournalSkeleton",
    );
    const skeleton = AccountJournalSkeleton({});
    expect(
      findAll(skeleton, (node) => node.type === "ActivityIndicator").length,
    ).toBe(0);
    // Six rows of icon, title, change and balance, under two date headers.
    expect(
      findAll(skeleton, (node) => node.type === "LoadingTile").length,
    ).toBe(6 * 4 + 2 * 2);
  });

  it("shows the error or empty message once loading is over", () => {
    const empty = AccountJournalListEmpty({
      loading: false,
      message: "No entries",
    });
    expect(
      findAll(empty, (node) => node.type === "Text").map((n) => n.children),
    ).toEqual([["No entries"]]);
  });

  it("restacks its rows at accessibility text sizes like AccountEntryRow", () => {
    fontScale = 1;
    const rowAt = () =>
      findAll(
        AccountJournalSkeleton({}),
        (node) =>
          node.type === "View" && flat(node.props.style).paddingVertical === 12,
      )[0];
    expect(flat(rowAt().props.style).flexDirection).toBe("row");
    fontScale = 2;
    expect(flat(rowAt().props.style).flexDirection).toBe("column");
    fontScale = 1;
  });
});

describe("Account detail list", () => {
  it("renders the shared empty state with the first-load flag", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "..", "account-detail-screen.tsx"),
      "utf8",
    );
    expect(source.includes("<AccountJournalListEmpty")).toBe(true);
    expect(source.includes("loading={isInitialLoading}")).toBe(true);
  });
});
