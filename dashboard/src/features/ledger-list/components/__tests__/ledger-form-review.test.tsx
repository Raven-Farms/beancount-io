import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as apolloClient from "@apollo/client/react";
import { GetCurrentUserDocument } from "@/graphql/definitions";
import { createMockQueryResult } from "@/test/apollo-test-utils";
import { LedgerForm } from "../ledger-form";

vi.mock("@apollo/client/react", () => ({
  useQuery: vi.fn(),
  useLazyQuery: vi.fn(() => [
    vi.fn(async () => ({ data: undefined })),
    { data: undefined, loading: false, error: undefined },
  ]),
}));
vi.mock(
  "@/common/providers/react-native-bridge-provider/react-native-bridge-context",
  () => ({ useReactNativeContext: () => ({ isReactNative: false }) }),
);
vi.mock("@tanstack/react-router", async () => {
  const { routerMock } = await import("@/test/mocks/router");
  return routerMock;
});

beforeEach(() => {
  sessionStorage.clear();
  vi.mocked(apolloClient.useQuery).mockImplementation(((document: unknown) =>
    createMockQueryResult({
      data:
        document === GetCurrentUserDocument
          ? {
              userProfile: {
                __typename: "UserProfileResponse",
                id: "user-1",
                tier: "FREE",
                username: "owner",
                email: "owner@example.test",
                firstName: null,
                lastName: null,
                locale: "en",
                emailReportStatus: null,
                limits: {
                  __typename: "UserLimits",
                  ledgersUsed: 0,
                  ledgersMax: 1,
                  collaboratorsPerLedgerMax: 1,
                },
              },
            }
          : { listLedgers: [] },
    })) as never);
});

const button = (name: string) => screen.getByRole("button", { name });
const review = () => screen.queryByTestId("ledger-create-review");

/** Only Review's Create Ledger creates the ledger (w4/314). */
describe("LedgerForm review step", () => {
  it("reaches Review by pointer and keyboard without creating, then creates once on confirm", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<LedgerForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await user.click(button("Next"));
    const detailsNext = button("Next");
    await user.click(detailsNext);
    expect(review()).toBeInTheDocument();
    // A browser runs the click's default action after React re-renders, so a
    // Next node reused as the submit button would create the ledger. jsdom
    // does not order it that way; the node identity is what must hold.
    expect(button("Create Ledger")).not.toBe(detailsNext);
    expect(detailsNext).not.toBeInTheDocument();

    await user.click(button("Back"));
    button("Next").focus();
    await user.keyboard("{Enter}");
    expect(review()).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();

    await user.click(button("Create Ledger"));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      name: "my-book",
      requestId: expect.any(String),
    });
  });

  it("advances instead of creating when Details is submitted from a field", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<LedgerForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await user.click(button("Next"));
    screen.getByLabelText("Ledger Name").closest("form")!.requestSubmit();
    await waitFor(() => expect(review()).toBeInTheDocument());
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
