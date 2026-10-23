import { describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { useRegisterForm } from "../use-register-form";

// Every sign-up form (register, OAuth and mobile consent) shows the refusal
// this hook picks. A password the server's policy refuses names its rule, so
// the reader is told why, not "some of the information provided is invalid".

const { signUp } = vi.hoisted(() => ({ signUp: vi.fn() }));
vi.mock("@apollo/client/react", () => ({ useMutation: () => [signUp] }));

const form = {
  email: "pat@example.org",
  username: "pat",
  password: "password123",
  confirmPassword: "password123",
};

async function submitRefusedWith(extensions: Record<string, unknown>) {
  signUp.mockRejectedValueOnce(
    new CombinedGraphQLErrors({ errors: [{ message: "refused", extensions }] }),
  );
  const onSuccess = vi.fn();
  const { result } = renderHook(() => useRegisterForm({ onSuccess }));
  await act(() => result.current.onSubmit(form));
  expect(onSuccess).not.toHaveBeenCalled();
  return result.current.serverError;
}

describe("useRegisterForm refusals", () => {
  it("says a breached password was refused for that", async () => {
    expect(
      await submitRefusedWith({
        code: "VALIDATION_FAILED",
        field: "password",
        passwordPolicy: "BREACHED",
      }),
    ).toBe(
      "This password has appeared in a data breach. Choose one you don't use anywhere else.",
    );
  });

  it("says a password too close to the email or username was refused", async () => {
    expect(
      await submitRefusedWith({
        code: "VALIDATION_FAILED",
        passwordPolicy: "TOO_SIMILAR",
      }),
    ).toBe("Password is too similar to your email or username.");
  });

  it("keeps the shared message for any other refusal", async () => {
    expect(await submitRefusedWith({ code: "CONFLICT" })).toBe(
      "This change conflicts with the current state. Please refresh and try again.",
    );
  });
});
