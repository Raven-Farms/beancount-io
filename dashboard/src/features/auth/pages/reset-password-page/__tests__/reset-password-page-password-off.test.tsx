import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import ResetPasswordPage from "../index";
import { resetAuthProvidersForTests } from "@/features/auth/hooks/use-auth-providers";

// Same router/Apollo mocks as reset-password-page.test.tsx: a valid token.
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  useSearch: () => ({ token: "valid-token" }),
  Link: ({ to, children }: { to: string; children: React.ReactNode }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("@apollo/client/react", () => ({
  useQuery: () => ({
    data: { validateEmailToken: { isValid: true } },
    loading: false,
    error: null,
  }),
  useMutation: vi.fn(() => [vi.fn(), { loading: false }]),
}));
vi.mock("@/common/components/seo/page-seo", () => ({ PageSEO: () => null }));

const providers = (body: unknown) =>
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => body,
  } as Response);

beforeEach(() => {
  resetAuthProvidersForTests();
});

afterEach(() => {
  vi.restoreAllMocks();
  resetAuthProvidersForTests();
});

describe("ResetPasswordPage when AUTH_PASSWORD_ENABLED=false", () => {
  it("offers Google instead of a new-password form, even with a valid token", async () => {
    providers({ google: true, password: false });
    const { container } = render(<ResetPasswordPage />);
    const link = await screen.findByRole("link", { name: /Google/ });
    expect(link.getAttribute("href")).toBe(
      "/api-gateway/auth/google/start?next=%2F",
    );
    expect(container.querySelector('input[type="password"]')).toBeNull();
    expect(screen.queryByRole("button", { name: "Reset password" })).toBeNull();
    expect(container.textContent).toContain("Password sign-in is turned off");
  });

  it("keeps the form when password sign-in is on", async () => {
    providers({ google: true, password: true });
    const { container } = render(<ResetPasswordPage />);
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
    expect(container.querySelector('input[type="password"]')).not.toBeNull();
  });
});
