import { MAX_LARGE_FILE_BYTES, withLargeContent } from "@/api/files";
import {
  Api as GiteaApi,
  type ContentsResponse,
} from "@/features/gitea/client/gitea-api";

const clientServing = (body: string | Uint8Array) =>
  new GiteaApi({
    baseUrl: "https://gitea.test/api/v1",
    baseApiParams: { format: "json" },
    customFetch: async () => new Response(body),
  });

// Gitea sends `content: null` for a large blob despite its spec.
const large = (over: Record<string, unknown> = {}): ContentsResponse =>
  ({
    name: "main.bean",
    path: "main.bean",
    type: "file",
    sha: "large-sha",
    size: 11_000_000,
    content: null,
    encoding: null,
    ...over,
  }) as unknown as ContentsResponse;

describe("withLargeContent (w21/343)", () => {
  it("fills a file Gitea returned with content null from the raw endpoint", async () => {
    const text = 'option "title" "Big"\n';
    const out = await withLargeContent(
      clientServing(text) as never,
      "alice",
      "book",
      large(),
    );
    expect(out.encoding).toBe("base64");
    expect(Buffer.from(out.content as string, "base64").toString("utf-8")).toBe(
      text,
    );
    expect(out.sha).toBe("large-sha");
  });

  it("leaves an inline file, an empty file and a directory untouched", async () => {
    const client = clientServing("never read") as never;
    const inline = large({ content: "aGk=", encoding: "base64", size: 2 });
    const empty = large({ size: 0 });
    const dir = large({ type: "dir" });
    expect(await withLargeContent(client, "a", "b", inline)).toBe(inline);
    expect(await withLargeContent(client, "a", "b", empty)).toBe(empty);
    expect(await withLargeContent(client, "a", "b", dir)).toBe(dir);
  });

  it("refuses a blob past the cap instead of returning an empty read", async () => {
    const client = new GiteaApi({
      baseUrl: "https://gitea.test/api/v1",
      baseApiParams: { format: "json" },
      customFetch: async () =>
        new Response("x", {
          headers: { "content-length": String(MAX_LARGE_FILE_BYTES + 1) },
        }),
    });
    await expect(
      withLargeContent(client as never, "a", "b", large()),
    ).rejects.toThrow();
  });
});
