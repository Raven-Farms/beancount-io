import {
  act,
  render,
  screen,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

const create = vi.hoisted(() => ({
  mutate: vi.fn(),
  navigate: vi.fn(),
}));

const blockerState = vi.hoisted(() => ({
  status: "idle" as "idle" | "blocked",
  reset: vi.fn(),
  proceed: vi.fn(),
  shouldBlockFn: null as null | (() => boolean),
  enableBeforeUnload: null as null | boolean | (() => boolean),
}));

vi.mock("@tanstack/react-router", () => ({
  useParams: () => ({
    ledgerOwner: "owner",
    ledgerName: "books",
    _splat: "",
  }),
  useNavigate: () => create.navigate,
  useBlocker: (opts: {
    shouldBlockFn: () => boolean;
    enableBeforeUnload?: boolean | (() => boolean);
  }) => {
    blockerState.shouldBlockFn = opts.shouldBlockFn;
    blockerState.enableBeforeUnload = opts.enableBeforeUnload ?? null;
    return blockerState;
  },
}));

vi.mock("@apollo/client/react", () => ({
  useMutation: () => [create.mutate],
  useQuery: () => ({ data: undefined }),
}));

vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ t: (key: string) => key }),
}));

vi.mock("@/common/lib/errors/error-message", () => ({
  useErrorMessage: () => (error: unknown) => String(error),
}));

vi.mock("@/common/hooks/use-theme", () => ({
  useIsDarkTheme: () => false,
}));

vi.mock("@/common/hooks/use-ledger", () => ({
  useLedger: () => ({ ledgerName: "books" }),
}));

// Drafting is writer-only behaviour; this suite is about the draft guard.
vi.mock("@/common/hooks/use-ledger-permission", () => ({
  useLedgerPermission: () => ({
    canWrite: true,
    canRead: true,
    isAdmin: false,
  }),
}));

vi.mock("@/common/components/monaco-editor", () => ({
  MonacoEditor: ({
    value,
    onChange,
    options,
  }: {
    value: string;
    onChange?: (value: string | undefined) => void;
    options?: { readOnly?: boolean };
  }) => (
    <textarea
      aria-label="file-content"
      value={value}
      readOnly={options?.readOnly}
      onChange={(e) => onChange?.(e.target.value)}
    />
  ),
}));

vi.mock("@/common/lib/editor/monaco-beancount-language", () => ({
  registerBeancountLanguage: vi.fn(),
}));

vi.mock("@/common/components/page-header", () => ({
  PageHeader: () => <div>header</div>,
}));

vi.mock("@/common/components/related-links", () => ({
  RelatedLinks: () => null,
}));

vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

import CreateFilePage from "../index";

/**
 * A pending Create File accepts no newer name or text: success leaves with
 * exactly the submitted draft, which is what it wrote (w4/247).
 */
describe("CreateFilePage while creating", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    blockerState.shouldBlockFn = null;
  });

  const name = () => screen.getByPlaceholderText("ledgerEditor.nameYourFile");
  const text = () => screen.getByLabelText("file-content");

  async function draftAndSave() {
    render(<CreateFilePage />);
    fireEvent.change(name(), { target: { value: "qa-create.txt" } });
    fireEvent.change(text(), { target: { value: "saved revision\n" } });
    fireEvent.click(screen.getByRole("button", { name: "common.save" }));
    await waitFor(() => expect(create.mutate).toHaveBeenCalledTimes(1));
  }

  it("locks both fields until the create settles, then leaves once", async () => {
    let finish!: () => void;
    create.mutate.mockImplementation(
      () => new Promise<void>((resolve) => (finish = resolve)),
    );
    await draftAndSave();

    expect(name()).toHaveAttribute("readonly");
    expect(text()).toHaveAttribute("readonly");
    fireEvent.change(name(), { target: { value: "qa-create-newer.txt" } });
    fireEvent.change(text(), { target: { value: "NEWER unsaved\n" } });
    expect(name()).toHaveValue("qa-create.txt");
    expect(text()).toHaveValue("saved revision\n");

    await act(async () => finish());
    expect(create.navigate).toHaveBeenCalledTimes(1);
    expect(create.mutate.mock.calls[0]![0].variables.path).toBe(
      "qa-create.txt",
    );
    // The departure is the submitted draft's own, so it is not blocked.
    expect(blockerState.shouldBlockFn?.()).toBe(false);
  });

  it("keeps the draft editable after a failed create", async () => {
    create.mutate.mockRejectedValue(new Error("offline"));
    await draftAndSave();

    await waitFor(() => expect(name()).not.toHaveAttribute("readonly"));
    expect(text()).not.toHaveAttribute("readonly");
    fireEvent.change(text(), { target: { value: "retry revision\n" } });
    expect(text()).toHaveValue("retry revision\n");
    expect(create.navigate).not.toHaveBeenCalled();
    expect(blockerState.shouldBlockFn?.()).toBe(true);
  });
});
