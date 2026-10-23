import fs from "fs";
import path from "path";
import vm from "vm";
import ts from "typescript";
import * as userDisplay from "../../../common/user-display";

// Execute the real component with a minimal React whose useState survives
// re-renders, so an image load failure can be followed to the next frame.
type Node = { type: string; props: Record<string, any>; children: any[] };
let states: unknown[] = [];
let cursor = 0;
const react = {
  createElement(type: any, props: any, ...children: any[]) {
    return typeof type === "function"
      ? type({ ...props, children })
      : { type, props: props ?? {}, children: children.flat() };
  },
  // Effects run as they are declared; the cursor-less stub is enough for a
  // component whose effect only reports.
  useEffect(effect: () => void) {
    effect();
  },
  useState(initial: unknown) {
    const slot = cursor++;
    if (!(slot in states)) states[slot] = initial;
    return [
      states[slot],
      (value: unknown) => {
        states[slot] = value;
      },
    ];
  },
};

function loadAvatar(): (props: Record<string, unknown>) => Node {
  const exports: Record<string, any> = {};
  const source = ts.transpileModule(
    fs.readFileSync(path.join(__dirname, "../index.tsx"), "utf8"),
    {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        jsx: ts.JsxEmit.React,
      },
    },
  ).outputText;
  vm.runInNewContext(source, {
    exports,
    React: react,
    require(id: string) {
      if (id === "react") return react;
      if (id === "react-native")
        return {
          Image: "Image",
          Text: "Text",
          View: "View",
          PixelRatio: { getPixelSizeForLayoutSize: (size: number) => size * 3 },
          StyleSheet: { create: (styles: unknown) => styles },
        };
      if (id === "@/common/theme")
        return {
          useTheme: () => ({
            colorTheme: { controlSelected: "tint", primary: "green" },
          }),
        };
      if (id === "@/common/user-display") return userDisplay;
      throw new Error(`Unexpected dependency: ${id}`);
    },
  });
  return exports.UserAvatar;
}

const realFetch = globalThis.fetch;
afterAll(() => {
  globalThis.fetch = realFetch;
});

const UserAvatar = loadAvatar();
const render = (props: Record<string, unknown>): Node => {
  cursor = 0;
  return UserAvatar(props);
};
const content = (tree: Node): Node => tree.children[0];

describe("UserAvatar", () => {
  beforeEach(() => {
    states = [];
  });

  it("shows initials when there is no picture", () => {
    const tree = render({ uri: null, name: "Ada Lovelace", size: 32 });
    expect(content(tree).type).toBe("Text");
    expect(content(tree).children).toEqual(["AL"]);
  });

  it("requests a sharp, fallible Gravatar image at the drawn size", () => {
    const tree = render({
      uri: "https://www.gravatar.com/avatar/abc?size=48",
      name: "Ada",
      size: 32,
    });
    expect(content(tree).type).toBe("Image");
    expect(content(tree).props.source.uri).toBe(
      "https://www.gravatar.com/avatar/abc?s=96&d=404",
    );
  });

  it("falls back to initials once the image fails, and stays there", () => {
    const props = {
      uri: "https://example.test/ada.png",
      name: "ada",
      size: 24,
    };
    content(render(props)).props.onError();
    const after = content(render(props));
    expect(after.type).toBe("Text");
    expect(after.children).toEqual(["A"]);
  });

  const answer = (status: number | Error) => {
    globalThis.fetch = (async () => {
      if (status instanceof Error) throw status;
      return { status };
    }) as unknown as typeof fetch;
  };
  const settle = () => new Promise((resolve) => setTimeout(resolve, 0));
  const failedAvatar = async (status: number | Error) => {
    states = [];
    answer(status);
    const reports: boolean[] = [];
    const props = {
      uri: "https://example.test/ada.png",
      name: "ada",
      size: 24,
      onFallbackChange: (fallback: boolean) => reports.push(fallback),
    };
    content(render(props)).props.onError();
    render(props);
    await settle();
    render(props);
    return reports;
  };

  it("reports there is no picture once the server says 404 (w21/289)", async () => {
    // The stub re-runs effects on every render: the last report is the state.
    const reports = await failedAvatar(404);
    expect(reports[0]).toBe(false);
    expect(reports[reports.length - 1]).toBe(true);
  });

  // w21/430: a failed load is not a missing Gravatar.
  it("does not report a picture that merely failed to load", async () => {
    expect((await failedAvatar(new Error("offline"))).includes(true)).toBe(
      false,
    );
    expect((await failedAvatar(503)).includes(true)).toBe(false);
  });

  it("reports no picture when there is none to load", () => {
    const none: boolean[] = [];
    render({
      uri: null,
      name: "ada",
      size: 24,
      onFallbackChange: (fallback: boolean) => none.push(fallback),
    });
    expect(none).toEqual([true]);
  });

  it("tries again when the picture changes after a failure", () => {
    content(
      render({ uri: "https://example.test/old.png", name: "ada", size: 24 }),
    ).props.onError();
    const next = content(
      render({ uri: "https://example.test/new.png", name: "ada", size: 24 }),
    );
    expect(next.type).toBe("Image");
  });

  it("is a circle of the requested size hidden from screen readers", () => {
    const tree = render({ name: "Ada", size: 40 });
    const style = Object.assign({}, ...tree.props.style);
    expect(style.width).toBe(40);
    expect(style.height).toBe(40);
    expect(style.borderRadius).toBe(20);
    expect(tree.props.accessible).toBe(false);
    expect(tree.props.importantForAccessibility).toBe("no-hide-descendants");
  });
});
