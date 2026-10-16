import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
} from "@apollo/client";
import { ApolloProvider } from "@apollo/client/react";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiKeysDocument } from "@/graphql/definitions";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import type { ApiKeyListItem } from "../api-key-utils";
import ApiKeysSettingsPage from "../index";

vi.unmock("react-i18next");
vi.unmock("@/common/hooks/use-translations");
vi.unmock("@/i18n");

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("@/common/components/seo/page-seo", () => ({
  PageSEO: () => null,
}));

const activeKey: ApiKeyListItem = {
  __typename: "ApiKeyType",
  id: "key-12345678-a",
  name: "Reporting",
  keyPrefix: "bcio_safe",
  scopes: ["ledger.read"],
  ledgerScope: "alice/books",
  lastUsedAt: null,
  expiresAt: null,
  revokedAt: null,
  createdAt: "2026-08-29T10:00:00.000Z",
};

describe("personal access token revocation", () => {
  it.each([
    ["en", "Revoke token {name}", "Revoke", "Cancel", "Revoked"],
    ["de", "Token {name} widerrufen", "Widerrufen", "Abbrechen", "Widerrufen"],
  ] as const)(
    "%s distinguishes same-name tokens with colliding dates and prefixes, preserves Cancel focus, and revokes only the confirmed ID",
    async (language, label, revokeText, cancelText, revokedText) => {
      const keys: ApiKeyListItem[] = [
        activeKey,
        { ...activeKey, id: "key-12345678-b" },
        { ...activeKey, id: "key-unique", name: "Importer" },
        {
          ...activeKey,
          id: "key-expired",
          name: "Expired job",
          expiresAt: "2020-01-01T00:00:00.000Z",
        },
        {
          ...activeKey,
          id: "key-revoked",
          name: "Retired job",
          revokedAt: "2026-08-29T11:00:00.000Z",
        },
      ];
      const operations: { name: string; variables: Record<string, unknown> }[] =
        [];
      let finishRevocation: (() => void) | undefined;
      const client = new ApolloClient({
        cache: new InMemoryCache(),
        link: new ApolloLink(
          (operation) =>
            new Observable((observer) => {
              operations.push({
                name: operation.operationName,
                variables: operation.variables,
              });
              if (operation.operationName === "ApiKeys") {
                observer.next({ data: { apiKeys: keys } });
                observer.complete();
                return;
              }
              if (operation.operationName === "RevokeApiKey") {
                const key = keys.find(
                  ({ id }) => id === operation.variables.id,
                );
                if (!key) throw new Error("Unexpected token ID");
                finishRevocation = () => {
                  observer.next({
                    data: {
                      revokeApiKey: {
                        ...key,
                        revokedAt: "2026-08-29T12:00:00.000Z",
                      },
                    },
                  });
                  observer.complete();
                };
                return;
              }
              observer.error(
                new Error(`Unexpected operation ${operation.operationName}`),
              );
            }),
        ),
      });
      const localization = createLocalization();
      await localization.changeLanguage(language);
      const view = render(
        <LocalizationProvider localization={localization}>
          <ApolloProvider client={client}>
            <ApiKeysSettingsPage />
          </ApolloProvider>
        </LocalizationProvider>,
      );
      try {
        const first = await screen.findByRole("button", {
          name: `${label.replace("{name}", "Reporting")} (ID: key-12345678-a)`,
          exact: true,
        });
        const second = screen.getByRole("button", {
          name: `${label.replace("{name}", "Reporting")} (ID: key-12345678-b)`,
          exact: true,
        });
        const unique = screen.getByRole("button", {
          name: label.replace("{name}", "Importer"),
          exact: true,
        });
        expect(first).toHaveTextContent(revokeText);
        expect(second).toHaveTextContent(revokeText);
        expect(unique).toHaveTextContent(revokeText);
        expect(screen.getAllByRole("button")).toHaveLength(4);
        expect(
          screen.queryByLabelText("Personal access token"),
        ).not.toBeInTheDocument();

        const user = userEvent.setup();
        await user.tab();
        await user.tab();
        expect(first).toHaveFocus();
        await user.keyboard("{Enter}");
        let dialog = await screen.findByRole("alertdialog");
        expect(dialog).toHaveAccessibleDescription(/Reporting/);
        const cancel = within(dialog).getByRole("button", {
          name: cancelText,
          exact: true,
        });
        await waitFor(() => expect(cancel).toHaveFocus());
        await user.keyboard("{Enter}");
        await waitFor(() => expect(first).toHaveFocus());
        expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
        expect(operations).toEqual([{ name: "ApiKeys", variables: {} }]);

        await user.tab();
        expect(second).toHaveFocus();
        await user.keyboard("{Enter}");
        dialog = await screen.findByRole("alertdialog");
        await waitFor(() =>
          expect(
            within(dialog).getByRole("button", {
              name: cancelText,
              exact: true,
            }),
          ).toHaveFocus(),
        );
        await user.tab();
        const confirm = within(dialog).getByRole("button", {
          name: revokeText,
          exact: true,
        });
        expect(confirm).toHaveFocus();
        await user.keyboard("{Enter}");
        await waitFor(() => expect(confirm).toBeDisabled());
        expect(
          within(dialog).getByRole("button", { name: cancelText, exact: true }),
        ).toBeDisabled();
        expect(operations).toEqual([
          { name: "ApiKeys", variables: {} },
          { name: "RevokeApiKey", variables: { id: "key-12345678-b" } },
        ]);

        await act(async () => finishRevocation?.());
        await waitFor(() =>
          expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument(),
        );
        expect(
          screen.getByRole("button", {
            name: `${label.replace("{name}", "Reporting")} (ID: key-12345678-a)`,
            exact: true,
          }),
        ).toBe(first);
        expect(
          screen.queryByRole("button", {
            name: `${label.replace("{name}", "Reporting")} (ID: key-12345678-b)`,
            exact: true,
          }),
        ).not.toBeInTheDocument();
        expect(screen.getAllByRole("button")).toHaveLength(3);
        expect(
          screen.getAllByText(revokedText, { exact: true }).length,
        ).toBeGreaterThanOrEqual(2);
        const cached = client.readQuery({ query: ApiKeysDocument })?.apiKeys;
        expect(
          cached?.find(({ id }) => id === activeKey.id)?.revokedAt,
        ).toBeNull();
        expect(
          cached?.find(({ id }) => id === "key-12345678-b")?.revokedAt,
        ).toBe("2026-08-29T12:00:00.000Z");
        expect(operations).toHaveLength(2);
      } finally {
        view.unmount();
        client.stop();
      }
    },
  );
});
