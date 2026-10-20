import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { describe, expect, it, vi } from "vitest";
import { TextFileView } from "../text-file-view";

vi.mock("@/common/hooks/use-ledger-permission", () => ({
  useLedgerPermission: () => ({ canWrite: true }),
}));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ t: (key: string) => key }),
}));
vi.mock("@/common/lib/utils/encode", () => ({
  base64Decode: (value: string) => value,
}));
vi.mock("../../../../shared/components/ledger-file-breadcrumb", () => ({
  default: ({ path }: { path: string }) => <span>{path}</span>,
}));
vi.mock("../../../hooks/use-normalized-line-number", () => ({
  useNormalizedLineNumber: (line?: number) => line,
}));
vi.mock("../../../hooks/use-platform", () => ({ useIsMac: () => true }));
vi.mock("../../non-text-file-views", () => ({
  FileMetadataBar: () => null,
  FileActionButtons: () => null,
}));
vi.mock("../text-editor", () => ({
  TextEditor: ({
    content,
    readOnly,
    setEditedContent,
  }: {
    content: string;
    readOnly?: boolean;
    setEditedContent?: (value: string) => void;
  }) => (
    <textarea
      aria-label="file-source"
      value={content}
      readOnly={readOnly}
      onChange={(event) => setEditedContent?.(event.target.value)}
    />
  ),
}));

/**
 * A successful save leaves edit mode once, without an unsaved-changes
 * prompt, and nothing typed while it is pending can be lost (w4/241).
 */
function setup(save: () => Promise<void>) {
  const onSave = vi.fn(save);
  const root = createRootRoute({ component: Outlet });
  const file = createRoute({
    getParentRoute: () => root,
    path: "/file",
    validateSearch: (search: Record<string, unknown>) => ({
      editMode: search.editMode === true || search.editMode === "true",
    }),
    component: function FileRoute() {
      const { editMode } = file.useSearch();
      const navigate = file.useNavigate();
      return (
        <TextFileView
          filePath="notes.txt"
          fileContent={{ content: "original\n", sha: "s", size: 9 } as never}
          onSave={onSave}
          onDelete={vi.fn()}
          isSaving={false}
          isEditMode={editMode}
          onEnterEditMode={() => void navigate({ search: { editMode: true } })}
          onExitEditMode={() => void navigate({ search: { editMode: false } })}
        />
      );
    },
  });
  const router = createRouter({
    routeTree: root.addChildren([file]),
    history: createMemoryHistory({ initialEntries: ["/file?editMode=true"] }),
  });
  render(<RouterProvider router={router} />);
  return { router, onSave };
}

const editor = () => screen.getByLabelText("file-source");

describe("TextFileView save lifecycle", () => {
  it("locks the source while saving, then exits edit mode without a prompt", async () => {
    let finish!: () => void;
    const { router, onSave } = setup(
      () => new Promise<void>((resolve) => (finish = resolve)),
    );
    fireEvent.change(await screen.findByLabelText("file-source"), {
      target: { value: "first revision\n" },
    });
    fireEvent.click(screen.getByRole("button", { name: "common.save" }));

    expect(editor()).toHaveAttribute("readonly");
    fireEvent.change(editor(), { target: { value: "second revision\n" } });
    expect(editor()).toHaveValue("first revision\n");

    await act(async () => finish());
    await waitFor(() =>
      expect(router.state.location.search).toEqual({ editMode: false }),
    );
    expect(screen.queryByText("ledgerEditor.unsavedChanges")).toBeNull();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(onSave).toHaveBeenCalledWith("first revision\n");
  });

  it("keeps the draft and the dirty guard after a failed save", async () => {
    const { router } = setup(() => Promise.reject(new Error("offline")));
    fireEvent.change(await screen.findByLabelText("file-source"), {
      target: { value: "unsaved draft\n" },
    });
    fireEvent.click(screen.getByRole("button", { name: "common.save" }));

    await waitFor(() => expect(editor()).not.toHaveAttribute("readonly"));
    expect(editor()).toHaveValue("unsaved draft\n");
    expect(router.state.location.search).toEqual({ editMode: true });

    fireEvent.click(screen.getByRole("button", { name: "common.cancel" }));
    expect(
      await screen.findByText("ledgerEditor.unsavedChanges"),
    ).toBeInTheDocument();
    expect(router.state.location.search).toEqual({ editMode: true });
  });
});
