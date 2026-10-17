import "reflect-metadata";
import { graphql, type GraphQLSchema } from "graphql";
import { buildSchema } from "type-graphql";
import { CommitsResolver } from "../commits-resolver";
import {
  CommitsService,
  type ICommitsService,
} from "../../service/commits-service";
import { IContext } from "@/server/graphql/context";
import { AuthorizationService } from "@/server/api/authorization";
import { UnauthenticatedError } from "@/shared/errors";

describe("CommitsResolver", () => {
  let resolver: CommitsResolver;
  let mockContext: jest.Mocked<IContext>;
  let mockService: jest.Mocked<ICommitsService>;

  beforeEach(() => {
    jest.clearAllMocks();

    mockService = {
      listCommits: jest.fn(),
      getCommitDetails: jest.fn(),
    } as unknown as jest.Mocked<ICommitsService>;

    resolver = new CommitsResolver(mockService);

    mockContext = {
      userId: "user123",
      identity: {
        userId: "user123",
        method: "session",
        scopes: new Set(),
      },
      getCurrentUser: jest.fn(),
    } as any;
  });

  describe("listCommits", () => {
    const ledgerId = "testowner/testledger";
    const branch = "main";
    const page = 1;
    const limit = 30;

    it("should list commits for authenticated user", async () => {
      const mockCommits = [
        {
          sha: "abc123",
          message: "Test commit",
          author: "Test Author",
          date: "2025-01-01T00:00:00Z",
        },
      ];

      mockService.listCommits.mockResolvedValue(mockCommits as any);

      const result = await resolver.listCommits(
        ledgerId,
        branch,
        page,
        limit,
        mockContext,
      );

      expect(result).toEqual(mockCommits);
      expect(mockService.listCommits).toHaveBeenCalledWith({
        identity: mockContext.identity,
        ledgerId,
        branch,
        page,
        limit,
      });
    });

    it("should list commits for anonymous user", async () => {
      const mockCommits = [{ sha: "abc123", message: "Test commit" }];
      mockContext.userId = undefined as any;
      mockContext.identity = undefined;
      mockService.listCommits.mockResolvedValue(mockCommits as any);

      const result = await resolver.listCommits(
        ledgerId,
        branch,
        page,
        limit,
        mockContext,
      );

      expect(result).toEqual(mockCommits);
      expect(mockService.listCommits).toHaveBeenCalledWith({
        identity: undefined,
        ledgerId,
        branch,
        page,
        limit,
      });
    });
  });

  describe("getCommitDetails", () => {
    const ledgerId = "testowner/testledger";
    const sha = "abc123";

    it("should get commit details for authenticated user", async () => {
      const mockDetails = {
        sha: "abc123",
        message: "Test commit",
        author: "Test Author",
        date: "2025-01-01T00:00:00Z",
        diff: "diff content",
        files: [],
      };

      mockService.getCommitDetails.mockResolvedValue(mockDetails as any);

      const result = await resolver.getCommitDetails(
        ledgerId,
        sha,
        mockContext,
      );

      expect(result).toEqual(mockDetails);
      expect(mockService.getCommitDetails).toHaveBeenCalledWith({
        identity: mockContext.identity,
        ledgerId,
        sha,
      });
    });

    it("should get commit details for anonymous user", async () => {
      const mockDetails = { sha: "abc123", message: "Test commit", files: [] };
      mockContext.userId = undefined as any;
      mockContext.identity = undefined;
      mockService.getCommitDetails.mockResolvedValue(mockDetails as any);

      const result = await resolver.getCommitDetails(
        ledgerId,
        sha,
        mockContext,
      );

      expect(result).toEqual(mockDetails);
      expect(mockService.getCommitDetails).toHaveBeenCalledWith({
        identity: undefined,
        ledgerId,
        sha,
      });
    });
  });
});

describe("CommitsResolver access through the GraphQL schema", () => {
  const PUBLIC_LEDGER = "open_ledger/example";
  const PRIVATE_LEDGER = "alice/private";
  const MEMBER = {
    userId: "usr_member",
    method: "session" as const,
    scopes: new Set<string>(),
  };
  const giteaCommit = {
    sha: "f281c34aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    commit: {
      message: "Add example",
      author: { name: "Ann", email: "ann@example.com", date: "2026-01-01" },
    },
    files: [{ filename: "main.beancount" }],
  };

  let schema: GraphQLSchema;
  let resolver: CommitsResolver;
  let repos: {
    repoGetAllCommits: jest.Mock;
    repoDownloadCommitDiffOrPatch: jest.Mock;
  };
  let factory: {
    getUserApiClient: jest.Mock;
    getAnonymousApiClient: jest.Mock;
  };

  // TypeGraphQL accumulates parameter metadata per build, so build once.
  beforeAll(async () => {
    schema = await buildSchema({
      resolvers: [CommitsResolver],
      container: { get: () => resolver },
      validate: false,
    });
  });

  beforeEach(() => {
    repos = {
      repoGetAllCommits: jest.fn().mockResolvedValue({ data: [giteaCommit] }),
      repoDownloadCommitDiffOrPatch: jest.fn().mockResolvedValue({ data: "" }),
    };
    factory = {
      getUserApiClient: jest.fn().mockResolvedValue({ repos }),
      getAnonymousApiClient: jest.fn().mockReturnValue({ repos }),
    };
    // Public ledgers grant read_contents to everyone, private ones to members.
    const authorization = new AuthorizationService(
      {
        check: jest.fn(
          async ({ user, object }) =>
            object === `ledger:${PUBLIC_LEDGER}` ||
            user === `user:${MEMBER.userId}`,
        ),
      },
      jest.fn(),
    );
    resolver = new CommitsResolver(
      new CommitsService(factory as never, authorization),
    );
  });

  const listCommits = (ledgerId: string, identity?: typeof MEMBER) =>
    graphql({
      schema,
      source: `query($ledgerId: String!) { listCommits(ledgerId: $ledgerId) { sha } }`,
      variableValues: { ledgerId },
      contextValue: { identity },
    });
  const getCommitDetails = (ledgerId: string, identity?: typeof MEMBER) =>
    graphql({
      schema,
      source: `query($ledgerId: String!, $sha: String!) {
        getCommitDetails(ledgerId: $ledgerId, sha: $sha) { sha message }
      }`,
      variableValues: { ledgerId, sha: giteaCommit.sha },
      contextValue: { identity },
    });

  it("lists a public ledger's history for an anonymous visitor", async () => {
    const result = await listCommits(PUBLIC_LEDGER);

    expect(result.errors).toBeUndefined();
    expect(result.data).toEqual({ listCommits: [{ sha: giteaCommit.sha }] });
    expect(factory.getAnonymousApiClient).toHaveBeenCalled();
    expect(factory.getUserApiClient).not.toHaveBeenCalled();
  });

  it("opens a public ledger's commit for an anonymous visitor", async () => {
    const result = await getCommitDetails(PUBLIC_LEDGER);

    expect(result.errors).toBeUndefined();
    expect(result.data).toEqual({
      getCommitDetails: { sha: giteaCommit.sha, message: "Add example" },
    });
    expect(factory.getAnonymousApiClient).toHaveBeenCalled();
  });

  it.each([
    ["listCommits", listCommits],
    ["getCommitDetails", getCommitDetails],
  ] as const)(
    "keeps a private ledger's %s from an anonymous visitor",
    async (_name, read) => {
      const result = await read(PRIVATE_LEDGER);

      expect(result.data).toBeNull();
      expect(result.errors?.[0]?.originalError).toBeInstanceOf(
        UnauthenticatedError,
      );
      expect(repos.repoGetAllCommits).not.toHaveBeenCalled();
    },
  );

  it.each([
    ["listCommits", listCommits],
    ["getCommitDetails", getCommitDetails],
  ] as const)(
    "serves a private ledger's %s to a member with their own client",
    async (_name, read) => {
      const result = await read(PRIVATE_LEDGER, MEMBER);

      expect(result.errors).toBeUndefined();
      expect(factory.getUserApiClient).toHaveBeenCalledWith(MEMBER.userId);
      expect(factory.getAnonymousApiClient).not.toHaveBeenCalled();
    },
  );
});
