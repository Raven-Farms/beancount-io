import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { KeyCreateDialog } from "../key-create-dialog";

vi.mock("@apollo/client/react", () => ({
  useMutation: () => [vi.fn(), { loading: false }],
}));

const catalogs = import.meta.glob<{
  default: Record<string, { message: string }>;
}>("../../../locales/*.ts", { eager: true });

describe("KeyCreateDialog public key guidance", () => {
  it("shows the OpenSSH key form with the real English catalog", () => {
    render(
      <KeyCreateDialog>
        <button type="button">New SSH key</button>
      </KeyCreateDialog>,
    );
    fireEvent.click(screen.getByRole("button", { name: "New SSH key" }));

    const publicKey = screen.getByLabelText("Public Key");
    expect(publicKey).toHaveAttribute(
      "placeholder",
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA…",
    );
    expect(
      screen.getByText(
        "Paste your public key here. It usually starts with ssh-ed25519 or ssh-rsa; print it with cat ~/.ssh/id_ed25519.pub. PEM public keys are also accepted.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/BEGIN PUBLIC KEY/)).toBeNull();
  });

  it("gives every locale the OpenSSH form rather than a PEM block", () => {
    const entries = Object.entries(catalogs);
    expect(entries).toHaveLength(15);
    for (const [path, { default: catalog }] of entries) {
      const description =
        catalog["userSettings.publicKeyDescription"]?.message ?? "";
      const placeholder =
        catalog["userSettings.publicKeyPlaceholder"]?.message ?? "";
      expect(description, path).toContain("ssh-ed25519");
      expect(description, path).toContain("cat ~/.ssh/id_ed25519.pub");
      expect(description, path).not.toContain("BEGIN PUBLIC KEY");
      expect(placeholder, path).toMatch(/^ssh-ed25519 AAAA/);
    }
  });
});
