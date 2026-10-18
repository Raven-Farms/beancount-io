import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  context: {} as Record<string, unknown>,
}));

vi.mock("@/common/hooks/use-root-context", () => ({
  useRootContext: () => state.context,
}));

import { Authenticated } from "../authenticated";

function renderGate() {
  return render(
    <Authenticated fallback={<div>Log In</div>}>
      <div>User menu</div>
    </Authenticated>,
  );
}

describe("Authenticated during an API outage (w3/646)", () => {
  it("shows the children when signed in", () => {
    state.context = { userProfile: { id: "u1" }, authStatus: "signed-in" };
    renderGate();
    expect(screen.getByText("User menu")).toBeInTheDocument();
    expect(screen.queryByText("Log In")).not.toBeInTheDocument();
  });

  it("shows the fallback only when genuinely signed out", () => {
    state.context = { userProfile: null, authStatus: "signed-out" };
    renderGate();
    expect(screen.getByText("Log In")).toBeInTheDocument();
    expect(screen.queryByText("User menu")).not.toBeInTheDocument();
  });

  it("shows neither children nor fallback while auth is unavailable", () => {
    state.context = { userProfile: null, authStatus: "unavailable" };
    renderGate();
    expect(screen.queryByText("Log In")).not.toBeInTheDocument();
    expect(screen.queryByText("User menu")).not.toBeInTheDocument();
  });
});
