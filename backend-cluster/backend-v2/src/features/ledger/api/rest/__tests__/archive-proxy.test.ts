import type { Readable } from "node:stream";
import { text } from "node:stream/consumers";
import { LedgerArchiveService } from "@/features/ledger/service/ledger-archive-service";
import {
  startArchiveOrigin,
  type ArchiveOrigin,
} from "@/features/ledger/service/__tests__/archive-origin";
import { BadUserInputError } from "@/shared/errors";
import { streamLedgerArchive } from "../archive-proxy";

let origin: ArchiveOrigin;
beforeAll(async () => {
  origin = await startArchiveOrigin();
});
afterAll(() => origin.close());

function context() {
  return {
    set: jest.fn(),
    throw: jest.fn(),
    body: undefined,
  } as any;
}

function layers() {
  const result = {
    database: {
      db: {},
      models: {
        user: {
          getById: jest.fn(),
          getUserByUsername: jest.fn(),
        },
      },
    },
    clients: { favaClientFactory: {} },
    services: {
      authorization: {
        authorizeOrThrow: jest.fn().mockResolvedValue({ allowed: true }),
      },
    },
  } as any;
  result.services.ledgerArchive = new LedgerArchiveService(
    result.database.models,
    result.database.db,
    { gitea: { internalBaseUrl: origin.url } } as never,
    result.services.authorization,
  );
  return result;
}

describe("streamLedgerArchive", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    origin.reset();
  });

  it("uses credential-free public access instead of the ledger owner's user", async () => {
    const appLayers = layers();
    const ctx = context();

    await streamLedgerArchive(ctx, appLayers, {
      ledgerId: "alice/public-ledger",
      archive: "gitea-main.zip",
    });

    expect(origin.requests.map((r) => r.url)).toEqual([
      "/api/v1/repos/alice/public-ledger/archive/gitea-main.zip",
    ]);
    expect(origin.requests[0].headers).not.toHaveProperty("authorization");
    expect(appLayers.database.models.user.getById).not.toHaveBeenCalled();
    expect(
      appLayers.database.models.user.getUserByUsername,
    ).not.toHaveBeenCalled();
    expect(ctx.set).toHaveBeenCalledWith("Cache-Control", "private, no-store");
    expect(ctx.set).toHaveBeenCalledWith("content-type", "application/zip");
    expect(await text(ctx.body as Readable)).toBe("ZIPBYTES");
  });

  it("rejects traversal before making an upstream request", async () => {
    await expect(
      streamLedgerArchive(context(), layers(), {
        ledgerId: "alice/public-ledger",
        archive: "../../private-ledger",
      }),
    ).rejects.toBeInstanceOf(BadUserInputError);
    expect(origin.requests).toHaveLength(0);
  });

  it("denies before user lookup, upstream fetch, or response headers", async () => {
    const appLayers = layers();
    appLayers.services.authorization.authorizeOrThrow.mockRejectedValueOnce(
      new Error("denied"),
    );
    const ctx = context();

    await expect(
      streamLedgerArchive(ctx, appLayers, {
        ledgerId: "alice/private",
        archive: "gitea-main.zip",
      }),
    ).rejects.toThrow("denied");
    expect(appLayers.database.models.user.getById).not.toHaveBeenCalled();
    expect(origin.requests).toHaveLength(0);
    expect(ctx.set).not.toHaveBeenCalled();
  });
});
