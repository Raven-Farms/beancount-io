import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
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

  it("RegisterForm keeps its fields when password sign-in is on", async () => {
    providers({ google: true, password: true });
    const { container } = render(
      <RegisterForm onSubmit={vi.fn()} isLoading={false} serverError="" />,
    );
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
    expect(container.querySelector('input[type="password"]')).not.toBeNull();
  });
});
