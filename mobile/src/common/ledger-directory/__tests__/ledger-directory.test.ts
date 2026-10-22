import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
  gql,
} from "@apollo/client";
import { LedgerDirectoryDocument } from "../../../generated-graphql/graphql";
import { LedgerDirectory, DIRECTORY_PAGE_SIZE } from "../ledger-directory";
import { getDrawerSections } from "../../../components/ledger-drawer/drawer-ledgers";

const ledger = (i: number) => ({
  __typename: "Ledger" as const,
  id: String(i),
  name: `book-${String(i).padStart(3, "0")}`,
  fullName: `owner/book-${String(i).padStart(3, "0")}`,
  description: null,
  private: true,
});

function setup(count = 31) {
  const state = {
    rows: Array.from({ length: count }, (_, i) => ledger(i)),
    pages: [] as number[],
    failPage: 0,
    repeatPage: false,
    holdPage: 0,
    release: () => {},
  };
  const client = new ApolloClient({
    cache: new InMemoryCache(),
    link: new ApolloLink(
      (operation) =>
        new Observable((observer) => {
          const { page, limit } = operation.variables;
          state.pages.push(page);
          expect(limit).toBe(DIRECTORY_PAGE_SIZE);
          const offset = state.repeatPage ? 0 : (page - 1) * limit;
          const rows = state.rows.slice(offset, offset + limit);
          const respond = () => {
            if (state.failPage === page) observer.error(new Error("offline"));
            else {
              observer.next({ data: { listLedgers: rows } });
              observer.complete();
            }
          };
          if (state.holdPage === page) state.release = respond;
          else respond();
        }),
    ),
  });
  return { client, state, directory: new LedgerDirectory(client) };
}

describe("cached ledger directory", () => {
  it("reads beyond page one, sorts independently of API order, and reuses cached pages", async () => {
    const { client, state, directory } = setup();
    state.rows.reverse();
    await directory.load();
    expect(state.pages).toEqual([1, 2]);
    expect(directory.getSnapshot().ledgers).toEqual([...state.rows].reverse());
    const reopened = new LedgerDirectory(client);
    await reopened.load();
    expect(state.pages).toEqual([1, 2]);
    expect(reopened.getSnapshot().ledgers).toEqual(
      directory.getSnapshot().ledgers,
    );
    client.stop();
  });

  it("keeps a newly created later-page ledger after switching away", async () => {
    const { client, state, directory } = setup(30);
    await directory.load();
    expect(state.pages).toEqual([1, 2]); // Full first page needs the empty terminator.
    const created = ledger(30);
    state.rows.push(created);
    await directory.refresh(created);
    const rows = directory.getSnapshot().ledgers;
    expect(rows.length).toBe(31);
    expect(state.pages).toEqual([1, 2, 1, 2]);
    expect(getDrawerSections(rows, created, "")).toEqual(
      getDrawerSections(rows, rows[0], ""),
    );
    expect(getDrawerSections(rows, rows[0], "book-030")[0].data).toEqual([
      created,
    ]);
    client.stop();
  });

  it("replaces refreshed pages rather than retaining deleted rows or old empty terminators", async () => {
    const { client, state, directory } = setup(61);
    await directory.load();
    state.rows = [ledger(90)];
    await directory.refresh();
    expect(directory.getSnapshot().ledgers).toEqual(state.rows);
    expect(
      client.readQuery({
        query: LedgerDirectoryDocument,
        variables: { page: 3, limit: 30 },
      }),
    ).toBe(null);
    client.stop();
  });

  it("retains confirmed creations and the previous list after a later-page refresh error", async () => {
    const { client, state, directory } = setup();
    await directory.load();
    const created = ledger(31);
    state.rows.push(created);
    state.failPage = 2;
    let failed = false;
    try {
      await directory.refresh(created);
    } catch {
      failed = true;
    }
    expect(failed).toBe(true);
    expect(directory.getSnapshot()).toEqual({
      ledgers: state.rows,
      loading: false,
      error: true,
    });
    state.failPage = 0;
    await directory.refresh();
    expect(directory.getSnapshot().error).toBe(false);
    client.stop();
  });

  it("does not shrink an existing complete directory while refreshing page one", async () => {
    const { client, state, directory } = setup();
    await directory.load();
    const sizes: number[] = [];
    const unsubscribe = directory.subscribe(() =>
      sizes.push(directory.getSnapshot().ledgers.length),
    );
    state.rows.push(ledger(31));
    await directory.refresh();
    expect(sizes).toEqual([31, 32]);
    unsubscribe();
    client.stop();
  });

  it("ignores old responses after refresh even when the transport ignores cancellation", async () => {
    const { client, state, directory } = setup(1);
    state.holdPage = 1;
    const old = directory.load();
    const releaseOld = state.release;
    state.holdPage = 0;
    state.rows = [ledger(99)];
    await directory.refresh();
    releaseOld();
    await old;
    expect(directory.getSnapshot().ledgers).toEqual(state.rows);
    expect(
      client.readQuery<any>({
        query: LedgerDirectoryDocument,
        variables: { page: 1, limit: 30 },
      })?.listLedgers,
    ).toEqual(state.rows);
    client.stop();
  });

  it("stops a server that repeats a full page instead of looping forever", async () => {
    const { client, state, directory } = setup(30);
    state.repeatPage = true;
    let failed = false;
    try {
      await directory.load();
    } catch {
      failed = true;
    }
    expect(failed).toBe(true);
    expect(state.pages).toEqual([1, 2]);
    expect(directory.getSnapshot().error).toBe(true);
    client.stop();
  });

  it("puts a public selection in its own section without changing the owner's list", async () => {
    const { client, directory } = setup(2);
    await directory.load();
    const rows = directory.getSnapshot().ledgers;
    const sections = getDrawerSections(rows, ledger(90), "");
    expect(sections[0].current).toBe(true);
    expect(sections[0].data).toEqual([ledger(90)]);
    expect(sections.slice(1)).toEqual(getDrawerSections(rows, rows[0], ""));
    client.stop();
  });
});

// w21/054: the drawer read the persisted cache and never asked again, so a
// ledger deleted on the web stayed listed through every relaunch.
describe("revalidating the directory on start", () => {
  it("shows the cached list, then drops a ledger the server no longer has", async () => {
    const { client, state, directory } = setup(3);
    await directory.load();
    // Deleted elsewhere, while the cached pages still hold it.
    state.rows = state.rows.filter((row) => row.id !== "2");
    const restarted = new LedgerDirectory(client);
    const seen: string[][] = [];
    restarted.subscribe(() =>
      seen.push(restarted.getSnapshot().ledgers.map((row) => row.id)),
    );
    await restarted.revalidate();
    // The cached rows first, then the server's.
    expect(seen.some((ids) => ids.includes("2"))).toBe(true);
    expect(restarted.getSnapshot().ledgers.map((row) => row.id)).toEqual([
      "0",
      "1",
    ]);
    expect(restarted.getSnapshot().error).toBe(false);
    client.stop();
  });

  it("keeps the cached list without an error when the revalidation fails", async () => {
    const { client, state, directory } = setup(3);
    await directory.load();
    state.failPage = 1;
    const restarted = new LedgerDirectory(client);
    await restarted.revalidate();
    expect(restarted.getSnapshot().ledgers.length).toBe(3);
    expect(restarted.getSnapshot().error).toBe(false);
    expect(restarted.getSnapshot().loading).toBe(false);
    client.stop();
  });
});

// w21/066: revalidation evicted the cached pages before fetching, so a failed
// offline revalidation left the persisted cache empty and the second offline
// launch showed no ledgers.
describe("an offline revalidation", () => {
  it("leaves the cached pages for the next offline launch", async () => {
    const { client, state, directory } = setup(3);
    await directory.load();
    state.failPage = 1;
    await new LedgerDirectory(client).revalidate();
    expect(
      client.readQuery<any>({
        query: LedgerDirectoryDocument,
        variables: { page: 1, limit: 30 },
      })?.listLedgers.length,
    ).toBe(3);
    const second = new LedgerDirectory(client);
    await second.revalidate();
    expect(second.getSnapshot()).toEqual({
      ledgers: state.rows,
      loading: false,
      error: false,
    });
    client.stop();
  });
});

// w21/391: a list cached before `description` joined the query missed in
// `readQuery`, the read went to the network, and offline the whole drawer list
// was dropped.
describe("a directory cached before the query gained description", () => {
  const OLD_QUERY = gql`
    query LedgerDirectory($page: Float!, $limit: Float!) {
      listLedgers(page: $page, limit: $limit) {
        id
        name
        fullName
        private
      }
    }
  `;

  function offlineWithOldCache(count = 3) {
    const cache = new InMemoryCache();
    const rows = Array.from({ length: count }, (_, i) => {
      const { description: _description, ...old } = ledger(i);
      return old;
    });
    cache.writeQuery({
      query: OLD_QUERY,
      variables: { page: 1, limit: DIRECTORY_PAGE_SIZE },
      data: { listLedgers: rows },
    });
    const client = new ApolloClient({
      cache,
      link: new ApolloLink(
        () =>
          new Observable((observer) => {
            observer.error(new Error("offline"));
          }),
      ),
    });
    return { client, directory: new LedgerDirectory(client), rows };
  }

  it("lists the cached ledgers offline, without an error", async () => {
    const { client, directory, rows } = offlineWithOldCache();
    await directory.revalidate();
    const snapshot = directory.getSnapshot();
    expect(snapshot.error).toBe(false);
    expect(snapshot.loading).toBe(false);
    expect(snapshot.ledgers.map((l) => l.id)).toEqual(rows.map((r) => r.id));
    // A description it never had reads as none.
    expect(snapshot.ledgers.every((l) => l.description === null)).toBe(true);
    client.stop();
  });

  it("still reports the failure when nothing is cached", async () => {
    const client = new ApolloClient({
      cache: new InMemoryCache(),
      link: new ApolloLink(
        () =>
          new Observable((observer) => {
            observer.error(new Error("offline"));
          }),
      ),
    });
    const directory = new LedgerDirectory(client);
    let failed = false;
    try {
      await directory.revalidate();
    } catch {
      failed = true;
    }
    expect(failed || directory.getSnapshot().error).toBe(true);
    client.stop();
  });
});
