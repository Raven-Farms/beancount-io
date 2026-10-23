import { describe, expect, it, vi } from "vitest";
import { redirectToLogin } from "../redirect-to-login";

describe("redirectToLogin", () => {
  it("replaces the current URL with the plain login URL", () => {
    const replace = vi.fn();

    redirectToLogin({ replace });

    expect(replace).toHaveBeenCalledWith("/auth/login");
  });
});
