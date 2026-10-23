import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
} from "@apollo/client";
import { ApolloProvider } from "@apollo/client/react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { GetCurrentUserQuery } from "@/graphql/definitions";
import { UserProfileSection } from "../user-profile-section";

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const PROFILE = {
  __typename: "UserProfileResponse",
  id: "user-1",
  email: "owner@example.test",
  username: "owner",
  firstName: "Ada",
  lastName: "Lovelace",
  locale: "en",
  emailReportStatus: null,
} as const;

const userData = { userProfile: PROFILE } as unknown as GetCurrentUserQuery;

type Held = {
  variables: Record<string, unknown>;
  succeed: () => void;
  fail: (error?: Record<string, unknown>) => void;
};

/**
 * A client that holds every profile write until the test settles it, so a
 * save stays pending for as long as the test needs.
 */
function profileClient() {
  const writes: Held[] = [];
  const client = new ApolloClient({
    cache: new InMemoryCache(),
    link: new ApolloLink(
      (operation) =>
        new Observable((observer) => {
          const name = operation.operationName;
          if (name === "UpdateProfile" || name === "UpdateUsername") {
            const field =
              name === "UpdateProfile" ? "updateProfile" : "updateUsername";
            writes.push({
              variables: operation.variables,
              succeed: () => {
                observer.next({
                  data: { [field]: { ...PROFILE, ...operation.variables } },
                });
                observer.complete();
              },
              fail: (error = { message: "Failed to fetch" }) => {
                observer.next({ data: null, errors: [error] } as never);
                observer.complete();
              },
            });
            return;
          }
          // The refetches after a landed write.
          observer.next({
            data:
              name === "ListLedgers"
                ? { listLedgers: [] }
                : { userProfile: null },
          });
          observer.complete();
        }),
    ),
  });
  return { client, writes };
}

function renderProfile() {
  const profile = profileClient();
  render(
    <ApolloProvider client={profile.client}>
      <UserProfileSection userData={userData} />
    </ApolloProvider>,
  );
  return profile;
}

async function openDialog(user: ReturnType<typeof userEvent.setup>, n = 0) {
  await user.click(screen.getAllByRole("button", { name: "Edit" })[n]);
  return screen.findByRole("dialog");
}

/** One pending profile save owns its dialog until it settles (w4/m47). */
describe("UserProfileSection pending saves", () => {
  it("sends one Change Name save from Enter, Enter and Save while it is pending", async () => {
    const user = userEvent.setup();
    const { writes } = renderProfile();
    const dialog = await openDialog(user);
    const first = within(dialog).getByLabelText("First Name");
    const last = within(dialog).getByLabelText("Last Name");

    await user.clear(first);
    await user.type(first, "  Grace ");
    await user.keyboard("{Enter}");
    await waitFor(() => expect(writes).toHaveLength(1));

    // Nothing else starts, and no edit is accepted into the sent draft.
    await user.click(last);
    await user.keyboard("{End} Hopper{Enter}");
    const save = within(dialog).getByRole("button", { name: /^updating/i });
    expect(save).toBeDisabled();
    await user.click(save);
    expect(writes).toHaveLength(1);
    expect(writes[0].variables).toEqual({
      firstName: "Grace",
      lastName: "Lovelace",
    });
    expect(last).toHaveValue("Lovelace");

    // A failure keeps the draft; one deliberate retry sends current values.
    writes[0].fail();
    await waitFor(() =>
      expect(
        within(dialog).getByRole("button", { name: "Save" }),
      ).toBeEnabled(),
    );
    expect(first).toHaveValue("  Grace ");
    await user.type(last, "-King");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(writes).toHaveLength(2));
    expect(writes[1].variables).toEqual({
      firstName: "Grace",
      lastName: "Lovelace-King",
    });

    writes[1].succeed();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("keeps a pending Change Name dialog open until its own save settles", async () => {
    const user = userEvent.setup();
    const { writes } = renderProfile();
    const dialog = await openDialog(user);
    const first = within(dialog).getByLabelText("First Name");
    await user.clear(first);
    await user.type(first, "Original");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(writes).toHaveLength(1));

    // Escape and the Close button wait for the save instead of dismissing.
    await user.keyboard("{Escape}");
    await user.click(within(dialog).getByRole("button", { name: /close/i }));
    expect(screen.getByRole("dialog")).toBe(dialog);
    expect(first).toHaveValue("Original");

    writes[0].succeed();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("returns focus from the parked dialog to Save when the save fails", async () => {
    const user = userEvent.setup();
    const { writes } = renderProfile();
    const dialog = await openDialog(user);
    const save = within(dialog).getByRole("button", { name: "Save" });
    save.focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(writes).toHaveLength(1));
    // The disabled Save cannot hold focus; the dialog's trap keeps it.
    expect(dialog).toHaveFocus();

    writes[0].fail();
    await waitFor(() => expect(save).toHaveFocus());
    expect(save).toBeEnabled();
    expect(screen.getByRole("dialog")).toBe(dialog);
  });

  it("holds a pending Change Username save the same way", async () => {
    const user = userEvent.setup();
    const { writes } = renderProfile();
    const dialog = await openDialog(user, 1);
    const input = within(dialog).getByRole("textbox", { name: "Username" });
    await user.clear(input);
    await user.type(input, "grace{Enter}");
    await waitFor(() => expect(writes).toHaveLength(1));

    await user.keyboard("x{Enter}");
    await user.keyboard("{Escape}");
    expect(writes).toHaveLength(1);
    expect(writes[0].variables).toEqual({ username: "grace" });
    expect(input).toHaveValue("grace");
    expect(screen.getByRole("dialog")).toBe(dialog);

    // A rule refusal stays on the field, with the draft and focus kept.
    writes[0].fail({
      message: "refused",
      extensions: { code: "BAD_USER_INPUT", field: "username" },
    });
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      /lowercase/i,
    );
    expect(input).toHaveValue("grace");
    expect(input).toHaveFocus();

    await user.keyboard("{Enter}");
    await waitFor(() => expect(writes).toHaveLength(2));
    writes[1].succeed();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});
