import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ForgotPasswordPage from "../index";
import { resetAuthProvidersForTests } from "@/features/auth/hooks/use-auth-providers";

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ to, children }: { to: string; children: React.ReactNode }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("@apollo/client/react", () => ({
  useMutation: vi.fn(() => [vi.fn(), { loading: false }]),
}));
vi.mock("@/common/components/seo/page-seo", () => ({ PageSEO: () => null }));

beforeEach(() => {
  resetAuthProvidersForTests();
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => ({ google: true, password: false }),
  } as Response);
});
afterEach(() => {
  vi.restoreAllMocks();
  resetAuthProvidersForTests();
  window.history.pushState({}, "", "/");
});

describe("ForgotPasswordPage when AUTH_PASSWORD_ENABLED=false", () => {
  it("sends Google on to the requested destination", async () => {
    window.history.pushState({}, "", "/auth/forgot-password?next=%2Fpricing");
    render(<ForgotPasswordPage />);
    const link = await screen.findByRole("link", { name: /Google/ });
    expect(link.getAttribute("href")).toBe(
      "/api-gateway/auth/google/start?next=%2Fpricing",
    );
  });

  it.each([undefined, "//evil.example"])(
    "falls back to / for next=%j",
    async (next) => {
      window.history.pushState(
        {},
        "",
        next
          ? `/auth/forgot-password?next=${encodeURIComponent(next)}`
          : "/auth/forgot-password",
      );
      render(<ForgotPasswordPage />);
      const link = await screen.findByRole("link", { name: /Google/ });
      expect(link.getAttribute("href")).toBe(
        "/api-gateway/auth/google/start?next=%2F",
      );
    },
  );
});
