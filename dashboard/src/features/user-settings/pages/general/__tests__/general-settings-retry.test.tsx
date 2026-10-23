import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
} from "@apollo/client";
import { ApolloProvider } from "@apollo/client/react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import GeneralSettingsPage from "../index";

vi.mock("@/common/components/seo/page-seo", () => ({ PageSEO: () => null }));
vi.mock(
  "@/common/providers/react-native-bridge-provider/react-native-bridge-context",
  () => ({
    useReactNativeContext: () => ({ isReactNative: true }),
  }),
);
vi.mock("../user-profile-section", () => ({
  UserProfileSection: ({
    userData,
  }: {
    userData?: { me?: { username?: string } };
  }) => (
    <section aria-label="User profile">
      {userData?.me?.username ?? "profile"}
    </section>
  ),
}));
vi.mock("../appearance-section", () => ({ AppearanceSection: () => null }));
vi.mock("../session-section", () => ({ SessionSection: () => null }));
vi.mock("../billing-summary-link", () => ({ BillingSummaryLink: () => null }));

/** A failed General Settings read offers an in-place retry (w4/257). */
describe("General Settings read failure", () => {
  it("retries the failed read from the keyboard and shows the profile", async () => {
    let calls = 0;
    const client = new ApolloClient({
      cache: new InMemoryCache(),
      link: new ApolloLink(
        () =>
          new Observable((observer) => {
            calls += 1;
            if (calls === 1) {
              observer.error(new Error("Failed to fetch"));
              return;
            }
            observer.next({ data: { me: null } });
            observer.complete();
          }),
      ),
    });
    render(
      <ApolloProvider client={client}>
        <GeneralSettingsPage />
      </ApolloProvider>,
    );

    const retry = await screen.findByRole("button", { name: "Try Again" });
    expect(screen.queryByRole("region", { name: "User profile" })).toBeNull();
    retry.focus();
    await userEvent.setup().keyboard("{Enter}");

    expect(
      await screen.findByRole("region", { name: "User profile" }),
    ).toBeInTheDocument();
    expect(calls).toBe(2);
  });
});
