import { CLI_AUTH_V1_ROUTES } from "../cli-auth-routes";

const logoutRoute = CLI_AUTH_V1_ROUTES.find((r) => r.operationId === "logout");

describe("REST v1 logout clears the session cookie with the configured Domain", () => {
  it.each([
    ["unset", undefined, ".beancount.io"],
    ["host-only", null, undefined],
    ["explicit", ".example.com", ".example.com"],
  ] as const)("production, %s", async (_label, cookieDomain, expected) => {
    const logout = jest.fn();
    const set = jest.fn();
    const ctx = {
      headers: { authorization: "Bearer t" },
      cookies: { set, get: jest.fn() },
    };
    await logoutRoute!.handler(
      {
        layers: { services: { auth: { logout } } },
        config: { env: "production", jwt: { cookieDomain } },
      } as never,
      { ctx } as never,
    );
    expect(logout).toHaveBeenCalledWith("t");
    expect(set).toHaveBeenCalledWith("authSess:beancount.io", "", {
      maxAge: 0,
      path: "/",
      ...(expected ? { domain: expected } : {}),
    });
  });
});
