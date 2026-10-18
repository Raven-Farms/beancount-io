import { render, screen } from "@testing-library/react";
import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { describe, expect, it, vi } from "vitest";
import LedgerFileView from "../index";

const state = vi.hoisted(() => ({ error: undefined as unknown }));

vi.mock("@apollo/client/react", () => ({
  useQuery: (document: { definitions: { name?: { value: string } }[] }) =>
    document.definitions[0]?.name?.value === "GetLedgerFile"
      ? { data: undefined, error: state.error }
      : { data: { getLedgerErrors: [] } },
  useMutation: () => [vi.fn()],
}));
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  useParams: () => ({}),
}));
vi.mock("@/common/hooks/use-file-navigate", () => ({
  useFileNavigate: () => vi.fn(),
}));
vi.mock("@/common/hooks/use-apollo-cache", () => ({
  useApolloCacheClear: () => vi.fn(),
}));

describe("a file the server refuses to read (w3/629)", () => {
  it("shows an unsafe path as not found, with no retry", () => {
    state.error = new CombinedGraphQLErrors({
      errors: [
        {
          message: "Invalid file path",
          extensions: { code: "BAD_USER_INPUT" },
        },
      ],
    });
    render(<LedgerFileView ledgerId="alice/books" filePath="../secret" />);

    expect(screen.getByText("File not found: ../secret")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Browse parent directory" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Try Again" })).toBeNull();
  });

  it("keeps Try Again for a real service failure", () => {
    state.error = new CombinedGraphQLErrors({
      errors: [
        {
          message: "Ledger API is temporarily unavailable",
          extensions: { code: "SERVICE_UNAVAILABLE" },
        },
      ],
    });
    render(<LedgerFileView ledgerId="alice/books" filePath="README.md" />);

    expect(
      screen.getByRole("button", { name: "Try Again" }),
    ).toBeInTheDocument();
  });
});
