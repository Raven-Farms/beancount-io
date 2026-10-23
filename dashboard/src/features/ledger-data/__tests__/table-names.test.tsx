import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useQuery } from "@apollo/client/react";
import LedgerDocumentsPage from "../documents/index";
import LedgerErrorsPage from "../errors/index";
import { CollaboratorsSection } from "../settings/collaborators-section";

/**
 * Every table in Ledger Data carries an accessible name (see
 * `features/ledger-data/AGENTS.md`); Documents, Errors and Collaborators did
 * not, in their loading or populated branches (w4/242).
 */
vi.mock("@tanstack/react-router", () => ({
  useParams: () => ({ ledgerOwner: "qa", ledgerName: "books" }),
  useNavigate: () => vi.fn(),
  Link: ({ children }: { children: React.ReactNode }) => (
    <a href="#">{children}</a>
  ),
}));
vi.mock("@apollo/client/react", () => ({
  useQuery: vi.fn(),
  useMutation: () => [vi.fn(), { loading: false }],
}));
vi.mock("@/common/hooks/use-ledger", () => ({
  useLedger: () => ({ ledgerName: "books" }),
}));
vi.mock("@/common/hooks/use-file-navigate", () => ({
  useFileNavigate: () => vi.fn(),
  getLedgerFilesRootPath: () => "/ledger/qa/books/files",
}));
vi.mock("@/common/components/related-links", () => ({
  RelatedLinks: () => null,
}));
vi.mock("@/common/hooks/use-user-limits", () => ({
  useUserLimits: () => ({ limits: null, tier: "FREE" }),
}));
vi.mock("@/common/components/ledger-permission/admin", () => ({
  LedgerAdminPermission: ({ children }: { children: React.ReactNode }) =>
    children,
}));
vi.mock(
  "@/features/collaboration/components/invite-collaborators-dialog",
  () => ({ InviteCollaboratorsDialog: () => null }),
);
vi.mock("@/features/collaboration/components/collaborator-row", () => ({
  CollaboratorRow: ({
    collaborator,
  }: {
    collaborator: { username: string };
  }) => (
    <tr>
      <td>{collaborator.username}</td>
    </tr>
  ),
}));

const respond = (state: { data?: unknown; loading?: boolean }) =>
  vi.mocked(useQuery).mockReturnValue({
    loading: false,
    error: undefined,
    ...state,
  } as never);

beforeEach(() => vi.clearAllMocks());

describe.each([
  {
    name: "Documents",
    view: <LedgerDocumentsPage />,
    data: {
      getLedgerDocuments: [
        {
          __typename: "LedgerDocument",
          date: "2026-10-20",
          account: "Assets:Cash",
          filename: "qa-document.txt",
          tags: [],
          links: [],
          meta: {},
        },
      ],
    },
  },
  {
    name: "Errors",
    view: <LedgerErrorsPage />,
    data: {
      getLedgerErrors: [
        { message: "Balance failed", filename: "main.bean", lineno: 91 },
      ],
    },
  },
  {
    name: "Collaborators",
    view: <CollaboratorsSection ledgerId="qa/books" />,
    data: {
      listLedgerCollaborators: [
        { username: "member", permission: "read", fullName: "", avatarUrl: "" },
      ],
    },
  },
])("$name table", ({ name, view, data }) => {
  it("is named while loading", () => {
    respond({ loading: true });
    render(view);
    // QueryView skeletons sit in an aria-hidden busy region; the table
    // still carries its name for when it is exposed.
    expect(
      screen.getByRole("table", { name, hidden: true }),
    ).toBeInTheDocument();
  });

  it("is named once populated", () => {
    respond({ data });
    render(view);
    expect(screen.getByRole("table", { name })).toBeInTheDocument();
  });
});
