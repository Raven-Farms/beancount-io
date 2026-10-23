import fs from "fs";
import path from "path";
import { buildSchema, parse, validate } from "graphql";
import {
  basicLedgerErrors,
  isUnknownFieldError,
  queryLedgerErrors,
} from "../ledger-errors-read";

/**
 * w21/591: `getLedgerErrors` gained `code` and `hint` on 2026-10-21, and a
 * server older than the app rejects a document that selects them: Notifications
 * failed, the bell read 0, and the editor's checks went silent, so a broken
 * ledger looked clean.
 */
const root = path.join(__dirname, "..", "..");
// The schema a server from before 2026-10-21 serves: the committed snapshot as
// it stood then, kept when the client was regenerated (w21/508).
const snapshot = fs.readFileSync(
  path.join(__dirname, "fixtures", "older-server.schema.graphql"),
  "utf8",
);
const document = (name: string) =>
  fs.readFileSync(
    path.join(root, "common", "graphql", "queries", `${name}.graphql`),
    "utf8",
  );

describe("the errors read against a server without code and hint", () => {
  it("has a document the older schema accepts", () => {
    const schema = buildSchema(snapshot);
    expect(validate(schema, parse(document("getLedgerErrorsBasic")))).toEqual(
      [],
    );
  });

  it("is the full document with only the later fields left out", () => {
    const fields = (text: string) =>
      [...text.matchAll(/^\s{4}(\w+)$/gm)].map((m) => m[1]);
    expect(fields(document("getLedgerErrors")).slice(0, 3)).toEqual(
      fields(document("getLedgerErrorsBasic")),
    );
  });

  it("recognises a server rejecting a field", () => {
    expect(
      isUnknownFieldError({
        graphQLErrors: [
          {
            message: 'Cannot query field "code" on type "BeancountError".',
            extensions: { code: "GRAPHQL_VALIDATION_FAILED" },
          },
        ],
      }),
    ).toBe(true);
    expect(
      isUnknownFieldError(new Error('Cannot query field "hint" on type X')),
    ).toBe(true);
    expect(isUnknownFieldError(new Error("Network request failed"))).toBe(
      false,
    );
    expect(isUnknownFieldError(undefined)).toBe(false);
  });

  it("lists the basic rows without a hint", () => {
    expect(
      basicLedgerErrors({
        getLedgerErrors: [{ filename: "a.bean", lineno: 3, message: "bad" }],
      }),
    ).toEqual([{ filename: "a.bean", lineno: 3, message: "bad", hint: null }]);
    expect(basicLedgerErrors(undefined)).toBe(undefined);
  });

  it("falls back to the basic read for a one-off check, and only for that failure", async () => {
    const rejected = Object.assign(new Error("validation"), {
      graphQLErrors: [
        {
          message: 'Cannot query field "code"',
          extensions: { code: "GRAPHQL_VALIDATION_FAILED" },
        },
      ],
    });
    const calls: string[] = [];
    const older = {
      query: async ({ query }: { query: { definitions: any[] } }) => {
        const name = query.definitions[0].name.value as string;
        calls.push(name);
        if (name === "getLedgerErrors") throw rejected;
        return {
          data: {
            getLedgerErrors: [
              { filename: "a.bean", lineno: 1, message: "broken" },
            ],
          },
        };
      },
    };
    const rows = await queryLedgerErrors(older as never, "alice/book");
    expect(calls).toEqual(["getLedgerErrors", "getLedgerErrorsBasic"]);
    expect(rows?.map((row) => row.message)).toEqual(["broken"]);

    const offline = {
      query: async () => {
        throw new Error("Network request failed");
      },
    };
    let thrown: unknown;
    try {
      await queryLedgerErrors(offline as never, "alice/book");
    } catch (error) {
      thrown = error;
    }
    expect((thrown as Error).message).toBe("Network request failed");
  });

  it("is what the hook and the editor use", () => {
    const read = (...parts: string[]) =>
      fs.readFileSync(path.join(root, ...parts), "utf8").replace(/\s+/g, "");
    const hook = read("common", "hooks", "use-ledger-errors.ts");
    expect(
      hook.includes("constolderServer=isUnknownFieldError(full.error);"),
    ).toBe(true);
    expect(hook.includes("skip:!ledgerId||!olderServer,")).toBe(true);
    expect(
      read("screens", "ledger-file-editor-screen", "index.tsx").includes(
        "after=awaitqueryLedgerErrors(client,ledgerId);",
      ),
    ).toBe(true);
  });
});

// w21/508: transaction detail selects `generated_from`, which a server older
// than 2026-10-21 rejects; it then reads the context without it.
describe("the entry context read against a server without generated_from", () => {
  it("rejects the full document, and accepts the one without the field", () => {
    const schema = buildSchema(snapshot);
    expect(
      validate(schema, parse(document("getLedgerTransactionContext"))).some(
        (error) => /generated_from/.test(error.message),
      ),
    ).toBe(true);
    expect(validate(schema, parse(document("getLedgerEntryContext")))).toEqual(
      [],
    );
  });

  it("falls back on that rejection, as the errors read does", () => {
    const hook = fs
      .readFileSync(
        path.join(
          root,
          "screens",
          "transaction-detail-screen",
          "use-transaction-context.ts",
        ),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(
      hook.includes("constolderServer=isUnsupportedDocumentError(full.error);"),
    ).toBe(true);
    expect(hook.includes("skip:skip||!olderServer")).toBe(true);
    expect(hook.includes("generatedFrom:olderServer?undefined")).toBe(true);
  });
});
