/**
 * Returning to the app refreshes what is on screen: mounted tabs otherwise kept
 * a transaction removed elsewhere and the old net worth (w21/024).
 *
 * Relative requires: the jest-lite runner has no `@/` alias for value imports.
 */
import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
  gql,
} from "@apollo/client";
import { APOLLO_DEFAULT_OPTIONS } from "../default-options";
import { createForegroundRefresher } from "../foreground-refresh";

describe("createForegroundRefresher", () => {
  const harness = (start = 0) => {
    let clock = start;
    const calls: number[] = [];
    const onChange = createForegroundRefresher({
      refresh: () => calls.push(clock),
      now: () => clock,
      minIntervalMs: 30_000,
    });
    return {
      calls,
      onChange,
      advance: (ms: number) => {
        clock += ms;
      },
    };
  };

  it("refreshes once on a return from the background", () => {
    const { calls, onChange } = harness();
    onChange("background");
    onChange("active");
    expect(calls.length).toBe(1);
  });

  it("does not refresh while staying active", () => {
    const { calls, onChange } = harness();
    onChange("active");
    onChange("active");
    expect(calls.length).toBe(0);
  });

  it("sends one refresh per window under rapid switching", () => {
    const { calls, onChange, advance } = harness();
    for (let i = 0; i < 5; i++) {
      onChange("inactive");
      onChange("active");
      advance(2_000);
    }
    expect(calls.length).toBe(1);
    advance(30_000);
    onChange("background");
    onChange("active");
    expect(calls.length).toBe(2);
  });
});

describe("foreground refresh with the app's default options", () => {
  it("brings a mounted query's rows up to date", async () => {
    let calls = 0;
    const link = new ApolloLink(
      () =>
        new Observable((observer) => {
          calls += 1;
          observer.next({
            data: {
              journal: [
                { __typename: "Row", payee: calls === 1 ? "refund" : "rent" },
              ],
            },
          });
          observer.complete();
        }),
    );
    const client = new ApolloClient({
      link,
      cache: new InMemoryCache(),
      defaultOptions: APOLLO_DEFAULT_OPTIONS,
    });
    const seen: string[] = [];
    const subscription = client
      .watchQuery({
        query: gql`
          query {
            journal {
              payee
            }
          }
        `,
      })
      .subscribe(({ data }) => {
        const rows = (data as { journal?: { payee: string }[] } | undefined)
          ?.journal;
        if (rows) seen.push(rows[0]!.payee);
      });
    await new Promise((resolve) => setTimeout(resolve, 30));

    const onChange = createForegroundRefresher({
      refresh: () => {
        void client.refetchQueries({ include: "active" });
      },
    });
    onChange("background");
    onChange("active");
    await new Promise((resolve) => setTimeout(resolve, 30));
    subscription.unsubscribe();

    expect(calls).toBe(2);
    expect(seen[seen.length - 1]).toBe("rent");
  });
});

describe("signed-in app", () => {
  it("mounts the foreground refresh for the whole session", () => {
    const fs = require("fs");
    const path = require("path");
    const layout = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "..",
        "..",
        "..",
        "app",
        "(app)",
        "_layout.tsx",
      ),
      "utf8",
    );
    expect(layout.includes("useForegroundRefresh(Boolean(session));")).toBe(
      true,
    );
  });
});
