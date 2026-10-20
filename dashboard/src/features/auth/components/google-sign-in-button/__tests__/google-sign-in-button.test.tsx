import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GoogleSignInButton } from "../index";
import { resetAuthProvidersForTests } from "@/features/auth/hooks/use-auth-providers";

const providers = (body: unknown, ok = true) =>
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok,
    json: async () => body,
  } as Response);

afterEach(() => {
  vi.restoreAllMocks();
  resetAuthProvidersForTests();
});

describe("GoogleSignInButton", () => {
  it("links to the ceremony on this origin when Google is offered", async () => {
    const fetch = providers({ google: true });
    render(<GoogleSignInButton next="/ledger/pat/books?tab=1" />);
    const link = await screen.findByRole("link");
    expect(link.getAttribute("href")).toBe(
      "/api-gateway/auth/google/start?next=%2Fledger%2Fpat%2Fbooks%3Ftab%3D1",
    );
    expect(fetch).toHaveBeenCalledWith(
      "/api-gateway/auth/providers",
      expect.anything(),
    );
  });

  it("drops an unsafe next instead of forwarding it", async () => {
    providers({ google: true });
    render(<GoogleSignInButton next="//evil.example" />);
    const link = await screen.findByRole("link");
    expect(link.getAttribute("href")).not.toContain("evil.example");
  });

  it.each([
    ["Google is not configured", () => providers({ google: false })],
    ["the probe fails", () => providers(null, false)],
    [
      "the probe throws",
      () => vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("x")),
    ],
  ])("renders nothing when %s", async (_label, arrange) => {
    const fetch = arrange();
    const { container } = render(<GoogleSignInButton next="/" />);
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(container.innerHTML).toBe("");
  });
});
