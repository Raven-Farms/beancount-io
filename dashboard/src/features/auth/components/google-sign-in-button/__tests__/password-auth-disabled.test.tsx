import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RegisterForm } from "@/features/auth/components/register-form";
import { ForgotPasswordForm } from "@/features/auth/components/forgot-password-form";
import { resetAuthProvidersForTests } from "@/features/auth/hooks/use-auth-providers";

vi.mock("@tanstack/react-router", () => ({
  Link: ({ to, children }: { to: string; children: React.ReactNode }) => (
    <a href={to}>{children}</a>
  ),
  useNavigate: () => vi.fn(),
}));
vi.mock("@apollo/client/react", () => ({
  useMutation: () => [vi.fn(), { loading: false }],
}));

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

// Every password form that could appear on its own (sign-up, consent-page
// sign-up, forgot password) yields to the notice when the server turns
// password sign-in off; reached directly, none of them can be submitted.
describe("password forms when AUTH_PASSWORD_ENABLED=false", () => {
  it("RegisterForm offers only Google", async () => {
    providers({ google: true, password: false });
    const { container } = render(
      <RegisterForm onSubmit={vi.fn()} isLoading={false} serverError="" />,
    );
    await screen.findByRole("link");
    expect(container.querySelector("input")).toBeNull();
  });

  it("ForgotPasswordForm explains instead of asking for an email", async () => {
    providers({ google: false, password: false });
    const { container } = render(<ForgotPasswordForm />);
    await waitFor(() => expect(container.querySelector("input")).toBeNull());
    expect(container.textContent).toContain("Password sign-in is turned off");
  });

  it("ForgotPasswordForm sends Google back to the destination it is given", async () => {
    providers({ google: true, password: false });
    window.history.pushState({}, "", "/auth/forgot-password");
    render(<ForgotPasswordForm googleNext="/" />);
    const link = await screen.findByRole("link", { name: /Google/ });
    expect(link.getAttribute("href")).toBe(
      "/api-gateway/auth/google/start?next=%2F",
    );
    window.history.pushState({}, "", "/");
  });

  it("an embedded ForgotPasswordForm keeps the page it is on (e.g. OAuth consent)", async () => {
    providers({ google: true, password: false });
    window.history.pushState({}, "", "/oauth/consent?uid=abc");
    render(<ForgotPasswordForm />);
    const link = await screen.findByRole("link", { name: /Google/ });
    expect(link.getAttribute("href")).toBe(
      "/api-gateway/auth/google/start?next=%2Foauth%2Fconsent%3Fuid%3Dabc",
    );
    window.history.pushState({}, "", "/");
  });

  it("asks again after a failed probe instead of caching the failure", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValue({
        ok: true,
        json: async () => ({ google: true, password: false }),
      } as Response);
    const first = render(<ForgotPasswordForm />);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(first.container.querySelector("input")).not.toBeNull(),
    );
    first.unmount();
    const second = render(<ForgotPasswordForm />);
    await screen.findByRole("link", { name: /Google/ });
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(second.container.querySelector("input")).toBeNull();
  });

  it("RegisterForm keeps its fields when password sign-in is on", async () => {
    providers({ google: true, password: true });
    const { container } = render(
      <RegisterForm onSubmit={vi.fn()} isLoading={false} serverError="" />,
    );
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
    expect(container.querySelector('input[type="password"]')).not.toBeNull();
  });
});
