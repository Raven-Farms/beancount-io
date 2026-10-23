import fs from "fs";
import path from "path";
import { collectPages } from "../collect-pages";

// w21/129: Starred stopped at 30 ledgers because the starred list's `total`
// is the page's own length, so search never found the 31st.
describe("collectPages", () => {
  const ledgers = Array.from({ length: 31 }, (_, i) => ({
    id: `qa/book-${i}`,
  }));
  const pageOf = (page: number) => ledgers.slice((page - 1) * 30, page * 30);

  it("reads past a full first page to the 31st ledger", async () => {
    const pages: number[] = [];
    const items = await collectPages(
      async (page) => {
        pages.push(page);
        return pageOf(page);
      },
      30,
      (item) => item.id,
    );
    expect(items.length).toBe(31);
    expect(items[30].id).toBe("qa/book-30");
    expect(pages).toEqual([1, 2]);
  });

  it("stops on a server that repeats a full page", async () => {
    let calls = 0;
    const items = await collectPages(
      async () => {
        calls += 1;
        return ledgers.slice(0, 30);
      },
      30,
      (item) => item.id,
    );
    expect(items.length).toBe(30);
    expect(calls).toBe(2);
  });

  it("is how Browse ledgers loads Starred and My ledgers", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "use-discovery.ts"),
      "utf8",
    );
    expect(source.includes("await collectPages<DiscoveryItem>(")).toBe(true);
    expect(source.includes("result.total")).toBe(false);
  });
});
