import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
  useNavigate,
  useSearch,
} from "@tanstack/react-router";
import { createContext, useCallback, useContext } from "react";
import type { EditorProps } from "@monaco-editor/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { GetLedgerFileQuery } from "@/graphql/definitions";
import { base64Encode } from "@/common/lib/utils/encode";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import { FileContentView } from "../file-content-view";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");

const boundary = vi.hoisted(() => ({
  canWrite: true,
  change: undefined as undefined | ((value: string) => void),
  mounts: 0,
}));
vi.mock("@/common/hooks/use-ledger-permission", () => ({
  useLedgerPermission: () => ({ canWrite: boundary.canWrite }),
}));

// Replace only Monaco's browser/runtime surface. TextEditor still owns its
// real options, keyboard listeners, buffer callback, and save callback.
vi.mock("@/common/components/monaco-editor", async () => {
  const { useEffect, useRef } = await import("react");
  return {
    MonacoEditor: (props: EditorProps) => {
      const latest = useRef(props);
      const input = useRef<HTMLTextAreaElement>(null);
      latest.current = props;
      boundary.change = (value) =>
        latest.current.onChange?.(value, {} as never);
      useEffect(() => {
        boundary.mounts += 1;
        const monaco = {
          KeyMod: { CtrlCmd: 1, Alt: 2 },
          KeyCode: { KeyD: 1, Slash: 2, BracketLeft: 3, BracketRight: 4 },
          languages: {
            register() {},
            setLanguageConfiguration() {},
            setMonarchTokensProvider() {},
            registerFoldingRangeProvider() {},
          },
          editor: {
            defineTheme() {},
            setTheme() {},
            setModelLanguage() {},
            setModelMarkers() {},
          },
        };
        const model = {
          getLineCount: () => (input.current?.value ?? "").split("\n").length,
          getLineMaxColumn: () => 1,
        };
        const editor = {
          getModel: () => model,
          getDomNode: () => input.current,
          getValue: () => input.current?.value ?? "",
          hasTextFocus: () => document.activeElement === input.current,
          focus: () => input.current?.focus(),
          addCommand() {},
          revealLine() {},
          revealLineInCenter() {},
          setPosition() {},
          deltaDecorations: () => [],
          trigger() {},
          getContribution: () => undefined,
        };
        latest.current.beforeMount?.(monaco as never);
        latest.current.onMount?.(editor as never, monaco as never);
      }, []);
      return (
        <textarea
          ref={input}
          aria-label="File source"
          aria-readonly={Boolean(props.options?.readOnly)}
          readOnly={Boolean(props.options?.readOnly)}
          value={props.value ?? ""}
          data-language={props.language}
          onChange={(event) =>
            props.onChange?.(event.target.value, {} as never)
          }
        />
      );
    },
  };
});

type FileContent = NonNullable<GetLedgerFileQuery["getLedgerFile"]>;
type Callbacks = {
  save: ReturnType<typeof vi.fn<(content: string) => Promise<void>>>;
  enter: ReturnType<typeof vi.fn>;
  exit: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};
const FixtureContext = createContext<{
  file: FileContent;
  calls: Callbacks;
  keepEditRequest: boolean;
} | null>(null);

function FileHarness() {
  const { file, calls, keepEditRequest } = useContext(FixtureContext)!;
  const { editMode } = useSearch({ strict: false });
  const navigate = useNavigate();
  const enter = useCallback(() => {
    calls.enter();
    void navigate({ to: ".", search: { editMode: true } });
  }, [calls, navigate]);
  const exit = useCallback(() => {
    calls.exit();
    if (keepEditRequest) return;
    void navigate({ to: ".", search: {}, replace: true });
  }, [calls, keepEditRequest, navigate]);
  return (
    <FileContentView
      filePath={file.path}
      fileContent={file}
      onSave={calls.save}
      onDelete={calls.delete}
      isSaving={false}
      isEditMode={editMode}
      onEnterEditMode={enter}
      onExitEditMode={exit}
    />
  );
}

function fileContent(
  path: string,
  text: string,
  overrides: Partial<FileContent> = {},
): FileContent {
  return {
    __typename: "LedgerFileContent",
    name: path.split("/").at(-1)!,
    path,
    content: base64Encode(text),
    size: new TextEncoder().encode(text).length,
    sha: "synthetic-sha",
    type: "file",
    encoding: "base64",
    lastCommitSha: "synthetic-commit",
    lastAuthorDate: null,
    lastCommitterDate: null,
    ...overrides,
  };
}

const originalUrlMethods = new Map(
  ["createObjectURL", "revokeObjectURL"].map(
    (name) => [name, Object.getOwnPropertyDescriptor(URL, name)] as const,
  ),
);
let downloadBlobs: Blob[];
let downloads: Array<{ filename: string; href: string }>;

beforeEach(() => {
  boundary.canWrite = true;
  boundary.change = undefined;
  boundary.mounts = 0;
  downloadBlobs = [];
  downloads = [];
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    writable: true,
    value: vi.fn((blob: Blob) => {
      downloadBlobs.push(blob);
      return "blob:synthetic-preview";
    }),
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    writable: true,
    value: vi.fn(),
  });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    downloads.push({ filename: this.download, href: this.href });
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  originalUrlMethods.forEach((descriptor, name) => {
    if (descriptor) Object.defineProperty(URL, name, descriptor);
    else Reflect.deleteProperty(URL, name);
  });
});

async function setup(
  file: FileContent,
  {
    editMode = false,
    canWrite = true,
    keepEditRequest = false,
    language = "en" as "en" | "fa",
  } = {},
) {
  boundary.canWrite = canWrite;
  const calls: Callbacks = {
    save: vi
      .fn<(content: string) => Promise<void>>()
      .mockResolvedValue(undefined),
    enter: vi.fn(),
    exit: vi.fn(),
    delete: vi.fn(),
  };
  const localization = createLocalization();
  await localization.changeLanguage(language);
  const root = createRootRoute({ component: () => <Outlet /> });
  const route = createRoute({
    getParentRoute: () => root,
    path: "/ledger/$ledgerOwner/$ledgerName/files/blob/$branch/$",
    validateSearch: (search: Record<string, unknown>) => ({
      editMode: search.editMode === true ? true : undefined,
    }),
    component: FileHarness,
  });
  const router = createRouter({
    routeTree: root.addChildren([route]),
    history: createMemoryHistory({
      initialEntries: [
        `/ledger/alice/books/files/blob/main/${file.path}${editMode ? "?editMode=true" : ""}`,
      ],
    }),
  });
  await router.load();
  const tree = (value: FileContent) => (
    <LocalizationProvider localization={localization}>
      <FixtureContext.Provider value={{ file: value, calls, keepEditRequest }}>
        <RouterProvider router={router} />
      </FixtureContext.Provider>
    </LocalizationProvider>
  );
  const view = render(tree(file));
  await screen.findByRole("heading", {
    name: new RegExp(file.name.replaceAll(".", "\\.")),
  });
  return {
    ...view,
    calls,
    router,
    localization,
    refresh: (next: FileContent) => view.rerender(tree(next)),
  };
}

describe("file content preview through the actual editor and actions", () => {
  it.each([
    ["statement.csv", "date,memo,amount\n2026-01-01,Café,-33.71\n"],
    ["pyproject.toml", '[project]\nname = "ledger-tools"\n'],
    [
      "statement.ofx",
      "OFXHEADER:100\n<OFX><BANKTRANLIST></BANKTRANLIST></OFX>\n",
    ],
    ["statement.qif", "!Type:Bank\nD01/01/2026\nT-33.71\nMCafé\n^\n"],
  ])(
    "previews the newly supported %s as exact source text",
    async (path, text) => {
      await setup(fileContent(path, text));
      const editor = screen.getByRole("textbox", { name: "File source" });
      expect(editor).toHaveValue(text);
      expect(editor).toHaveAttribute("readonly");
      expect(screen.getByRole("button", { name: /^Edit/ })).toBeInTheDocument();
    },
  );

  it.each(["en", "fa"] as const)(
    "keeps an unknown UTF-8 dotfile read-only for a %s writer despite a forced edit URL and shortcuts",
    async (language) => {
      const text = "# یادداشت\nOriginal memo: Café\n";
      const { calls, router, localization } = await setup(
        fileContent(".verify-m15", text),
        { editMode: true, language },
      );
      const editor = screen.getByRole("textbox", { name: "File source" });
      expect(editor).toHaveValue(text);
      expect(editor).toHaveAttribute("readonly");
      expect(editor).toHaveAttribute("aria-readonly", "true");
      expect(
        screen.queryByRole("button", {
          name: new RegExp(`^${localization.i18n.t("common.edit")}`),
        }),
      ).not.toBeInTheDocument();
      await waitFor(() =>
        expect(router.state.location.search.editMode).toBeUndefined(),
      );
      for (const modifiers of [{ metaKey: true }, { ctrlKey: true }]) {
        fireEvent.keyDown(document, { key: "e", ...modifiers });
        fireEvent.keyDown(document, { key: "s", ...modifiers });
      }
      act(() => boundary.change?.("UNAUTHORIZED REPLACEMENT"));
      expect(editor).toHaveValue(text);
      expect(calls.enter).not.toHaveBeenCalled();
      expect(calls.save).not.toHaveBeenCalled();
      expect(calls.delete).not.toHaveBeenCalled();
      expect(calls.exit).toHaveBeenCalledTimes(1);
    },
  );

  it("retains the existing .env.example text preview", async () => {
    await setup(
      fileContent(".env.example", "EXAMPLE_URL=https://example.invalid\n"),
    );
    expect(screen.getByRole("textbox", { name: "File source" })).toHaveValue(
      "EXAMPLE_URL=https://example.invalid\n",
    );
  });

  it("refreshes an unknown text extension without remounting or retaining a draft under a persistent forced edit request", async () => {
    const original = fileContent("notes.custom", "Original café memo\n");
    const { refresh, calls, router } = await setup(original, {
      editMode: true,
      keepEditRequest: true,
    });
    const editor = screen.getByRole("textbox", { name: "File source" });
    expect(editor).toHaveValue("Original café memo\n");
    act(() => boundary.change?.("UNAUTHORIZED DRAFT"));
    refresh(
      fileContent("notes.custom", "Refreshed یادداشت\n", {
        sha: "refreshed-sha",
      }),
    );
    expect(editor).toHaveValue("Refreshed یادداشت\n");
    expect(editor).toHaveAttribute("readonly");
    expect(boundary.mounts).toBe(1);
    expect(router.state.location.search.editMode).toBe(true);
    expect(calls.exit).toHaveBeenCalledTimes(1);
    expect(calls.save).not.toHaveBeenCalled();
    expect(calls.enter).not.toHaveBeenCalled();
  });

  it.each([
    ["archive.zip", btoa("PK\x03\x04\0\x14"), 6],
    ["nul.custom", btoa("hello\0world"), 11],
    ["invalid.custom", btoa("\xc3\x28"), 2],
    [
      "oversize.custom",
      base64Encode("small payload with over-cap metadata"),
      1024 * 1024 + 1,
    ],
  ] as const)(
    "keeps %s unsupported instead of mounting a text editor",
    async (path, content, size) => {
      await setup(fileContent(path, "", { content, size }));
      expect(screen.getByText("Unsupported file format")).toBeInTheDocument();
      expect(
        screen.queryByRole("textbox", { name: "File source" }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /^Edit/ }),
      ).not.toBeInTheDocument();
      expect(boundary.mounts).toBe(0);
    },
  );

  it.each(["toolbar", "keyboard"] as const)(
    "lets a writer edit known CSV and save exact content through the real %s action",
    async (method) => {
      const { calls, router } = await setup(
        fileContent("statement.csv", "date,amount\n2026-01-01,-33.71\n"),
      );
      const user = userEvent.setup();
      await user.click(screen.getByRole("button", { name: /^Edit/ }));
      const editor = screen.getByRole("textbox", { name: "File source" });
      await waitFor(() => expect(editor).not.toHaveAttribute("readonly"));
      expect(router.state.location.search.editMode).toBe(true);
      const draft = "date,amount\n2026-01-01,-33.7100000000001\n";
      fireEvent.change(editor, { target: { value: draft } });
      expect(editor).toHaveValue(draft);
      if (method === "toolbar")
        await user.click(screen.getByRole("button", { name: "Save" }));
      else fireEvent.keyDown(document, { key: "s", metaKey: true });
      await waitFor(() =>
        expect(calls.save).toHaveBeenCalledExactlyOnceWith(draft),
      );
      expect(calls.enter).toHaveBeenCalledTimes(1);
      expect(calls.delete).not.toHaveBeenCalled();
      expect(boundary.mounts).toBe(1);
    },
  );

  it("denies a reader's known-text forced edit URL, shortcuts, and raw editor changes", async () => {
    const text = "EXAMPLE_FLAG=sample\n";
    const { calls, router } = await setup(fileContent(".env.example", text), {
      canWrite: false,
      editMode: true,
    });
    const editor = screen.getByRole("textbox", { name: "File source" });
    expect(editor).toHaveAttribute("readonly");
    expect(
      screen.queryByRole("button", { name: /^Edit/ }),
    ).not.toBeInTheDocument();
    for (const modifiers of [{ ctrlKey: true }, { metaKey: true }]) {
      fireEvent.keyDown(document, { key: "e", ...modifiers });
      fireEvent.keyDown(document, { key: "s", ...modifiers });
    }
    act(() => boundary.change?.("UNAUTHORIZED READER DRAFT"));
    expect(editor).toHaveValue(text);
    expect(calls.enter).not.toHaveBeenCalled();
    expect(calls.save).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(router.state.location.search.editMode).toBeUndefined(),
    );
    expect(calls.exit).toHaveBeenCalledTimes(1);
  });

  it.each(["receipt.pdf", "receipt.png"])(
    "preserves the %s viewer and original download payload",
    async (path) => {
      const file = fileContent(
        path,
        path.endsWith(".pdf")
          ? "%PDF-1.4\nSynthetic receipt"
          : "Synthetic image bytes",
      );
      const { calls } = await setup(file);
      if (path.endsWith(".pdf")) {
        expect(screen.getByTitle(path)).toHaveAttribute(
          "src",
          `data:application/pdf;base64,${file.content}`,
        );
      } else {
        expect(screen.getByRole("img", { name: path })).toHaveAttribute(
          "src",
          `data:image/png;base64,${file.content}`,
        );
      }
      expect(
        screen.queryByRole("textbox", { name: "File source" }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /^Edit/ }),
      ).not.toBeInTheDocument();
      const user = userEvent.setup();
      await user.click(screen.getByRole("button", { name: "More actions" }));
      await user.click(
        await screen.findByRole("menuitem", { name: "Download" }),
      );
      expect(downloads).toEqual([
        {
          filename: path,
          href: `data:${path.endsWith(".png") ? "image/png" : "application/octet-stream"};base64,${file.content}`,
        },
      ]);
      expect(downloadBlobs).toEqual([]);
      expect(calls.save).not.toHaveBeenCalled();
      expect(calls.delete).not.toHaveBeenCalled();
    },
  );

  it.each(["statement.csv", "notes.custom"])(
    "downloads %s without changing source text or filename",
    async (path) => {
      const text =
        "date,memo,amount\n2026-01-01,Café یادداشت,-33.7100000000001\n";
      const file = fileContent(path, text);
      const { calls } = await setup(file);
      const user = userEvent.setup();
      await user.click(screen.getByRole("button", { name: "More actions" }));
      await user.click(
        await screen.findByRole("menuitem", { name: "Download" }),
      );
      if (path.endsWith(".csv")) {
        expect(downloads).toEqual([
          { filename: path, href: "blob:synthetic-preview" },
        ]);
        expect(downloadBlobs).toHaveLength(1);
        const decoded = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result));
          reader.onerror = reject;
          reader.readAsText(downloadBlobs[0]);
        });
        expect(decoded).toBe(text);
        expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith(
          "blob:synthetic-preview",
        );
      } else {
        expect(downloads).toEqual([
          {
            filename: path,
            href: `data:application/octet-stream;base64,${file.content}`,
          },
        ]);
        expect(downloadBlobs).toEqual([]);
      }
      expect(calls.save).not.toHaveBeenCalled();
      expect(calls.delete).not.toHaveBeenCalled();
    },
  );
});
