import { text } from "node:stream/consumers";
import type { Identity } from "@/server/api/identity";
import { NotFoundError, ServiceUnavailableError } from "@/shared/errors";
import { ARCHIVE_HEADERS_TIMEOUT_MS } from "../ledger-archive-service";
import {
  archiveServiceFor,
  closed,
  startArchiveOrigin,
  type ArchiveOrigin,
} from "./archive-origin";

/** The archive download against a real HTTP origin standing in for Gitea (w0/m8). */
const alice = { userId: "usr_alice" } as Identity;

describe("LedgerArchiveService", () => {
  let origin: ArchiveOrigin;
  beforeEach(async () => {
    origin = await startArchiveOrigin();
  });
  afterEach(async () => {
    jest.restoreAllMocks();
    await origin.close();
  });

  const download = (identity?: Identity, archive = "main.zip") =>
    archiveServiceFor(origin).download({
      identity,
      ledgerId: identity ? "alice/main" : "alice/public",
      archive,
    });

  it("reads Gitea's archive API with the caller's Gitea credentials", async () => {
    const archive = await download(alice);
    expect(await text(archive.body)).toBe("ZIPBYTES");
    expect(archive).toMatchObject({
      contentType: "application/zip",
      contentDisposition: 'attachment; filename="main.zip"',
    });
    expect(origin.requests.map((r) => r.url)).toEqual([
      "/api/v1/repos/alice/main/archive/main.zip",
    ]);
    expect(origin.requests[0].headers.authorization).toBe(
      `Basic ${Buffer.from("alice:fixture-only").toString("base64")}`,
    );
  });

  it("sends no credential at all for an anonymous public read", async () => {
    const archive = await download(undefined, "main.tar.gz");
    await text(archive.body);
    expect(origin.requests[0].url).toBe(
      "/api/v1/repos/alice/public/archive/main.tar.gz",
    );
    expect(origin.requests[0].headers).not.toHaveProperty("authorization");
  });

  it.each([
    [404, NotFoundError],
    [401, ServiceUnavailableError],
    [500, ServiceUnavailableError],
  ])("maps Gitea %s to %p", async (status, error) => {
    origin.serve((_req, res) => {
      res.statusCode = status;
      res.end("upstream failure");
    });
    await expect(download(alice)).rejects.toBeInstanceOf(error);
  });

  it("fails as unavailable when Gitea sends no headers before the deadline", async () => {
    const timers = jest.spyOn(global, "setTimeout");
    origin.serve(() => {
      // Never answers.
    });
    const pending = download(alice);
    while (origin.requests.length === 0)
      await new Promise((resolve) => setImmediate(resolve));
    const deadline = timers.mock.calls.find(
      ([, ms]) => ms === ARCHIVE_HEADERS_TIMEOUT_MS,
    );
    expect(deadline).toBeDefined();
    const upstream = closed(origin.requests[0]);
    (deadline![0] as () => void)();
    await expect(pending).rejects.toBeInstanceOf(ServiceUnavailableError);
    expect(await upstream).toBe("closed");
  });

  it("clears the deadline once headers arrive, however long the body takes", async () => {
    const set = jest.spyOn(global, "setTimeout");
    const clear = jest.spyOn(global, "clearTimeout");
    const archive = await download(alice);
    const index = set.mock.calls.findIndex(
      ([, ms]) => ms === ARCHIVE_HEADERS_TIMEOUT_MS,
    );
    expect(clear).toHaveBeenCalledWith(set.mock.results[index].value);
    expect(await text(archive.body)).toBe("ZIPBYTES");
  });

  it("ends the Gitea request when the body is destroyed mid-download", async () => {
    origin.serve((_req, res) => {
      // A large archive: one chunk now, the rest never — only the caller ends it.
      res.write(Buffer.alloc(64 * 1024));
    });
    const archive = await download(alice);
    await new Promise((resolve) => archive.body.once("data", resolve));
    const upstream = closed(origin.requests[0]);
    archive.body.destroy();
    expect(await upstream).toBe("closed");
  });
});
