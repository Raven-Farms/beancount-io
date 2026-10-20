import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LoginForm } from "../index";
import { resetAuthProvidersForTests } from "@/features/auth/hooks/use-auth-providers";

vi.mock("@tanstack/react-router", () => ({
  Link: ({ to, children }: { to: string; children: React.ReactNode }) => (
    <a href={to}>{children}</a>
  ),
}));

const props = {
  onSubmit: vi.fn().mockResolvedValue(undefined),
  isLoading: false,
  serverError: "",
};

const providers = (body: unknown) =>
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => body,
  } as Response);

afterEach(() => {
  vi.restoreAllMocks();
  resetAuthProvidersForTests();
});

describe("LoginForm and the server's sign-in methods", () => {
  it("shows only Continue with Google when password sign-in is off", async () => {
    providers({ google: true, password: false });
    const { container } = render(<LoginForm {...props} googleNext="/x" />);
    const link = await screen.findByRole("link");
    expect(link.getAttribute("href")).toBe(
      "/api-gateway/auth/google/start?next=%2Fx",
    );
    expect(container.querySelector("input")).toBeNull();
  });

  it("keeps the password form, with Google beside it, when both are on", async () => {
    providers({ google: true, password: true });
    const { container } = render(<LoginForm {...props} googleNext="/x" />);
    await waitFor(() =>
      expect(
        container.querySelector('a[href^="/api-gateway/auth/google/start"]'),
      ).not.toBeNull(),
    );
    expect(container.querySelector('input[type="password"]')).not.toBeNull();
  });

  it("keeps the password form when the server cannot be asked", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));
    const { container } = render(<LoginForm {...props} />);
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
    expect(container.querySelector('input[type="password"]')).not.toBeNull();
    expect(
      container.querySelector('a[href^="/api-gateway/auth/google/start"]'),
    ).toBeNull();
  });
});
