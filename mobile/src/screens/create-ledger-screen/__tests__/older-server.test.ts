import fs from "fs";
import path from "path";
import { buildSchema, parse, validate } from "graphql";
import { isUnsupportedDocumentError } from "../../../common/graphql-unsupported";
import { previewFailureKind } from "../ledger-name";
import { translationLocales } from "../../../translations/__tests__/locale-parity";

/**
 * w21/592: creating a ledger failed on any server older than 2026-10-20, even
 * for Starter and Sample, because the document always declared `setup` and
 * `requestId`; a preset showed an endless Retry. ADR021: older backends keep
 * working, and a rejected `setup` means "this server does not support guided
 * setup".
 */
const root = path.join(__dirname, "..", "..", "..");
// An older server's schema, kept apart from the regenerated snapshot (w21/508).
const snapshot = fs.readFileSync(
  path.join(
    root,
    "common",
    "__tests__",
    "fixtures",
    "older-server.schema.graphql",
  ),
  "utf8",
);
const document = (name: string) => {
  const dir = path.join(root, "common", "graphql");
  for (const folder of fs.readdirSync(dir)) {
    const file = path.join(dir, folder, `${name}.graphql`);
    if (fs.existsSync(file)) return fs.readFileSync(file, "utf8");
  }
  throw new Error(`no document ${name}`);
};

describe("creating a ledger against an older schema", () => {
  it("has a document without the new arguments that the older schema accepts", () => {
    const schema = buildSchema(snapshot);
    expect(validate(schema, parse(document("createLedgerBasic")))).toEqual([]);
  });

  it("is why the full document needs the fallback, while the snapshot predates setup", () => {
    if (snapshot.includes("LedgerSetupInput")) return;
    const schema = buildSchema(snapshot);
    const errors = validate(schema, parse(document("createLedger")));
    expect(errors.length > 0).toBe(true);
    expect(errors.some((e) => /LedgerSetupInput|setup/.test(e.message))).toBe(
      true,
    );
  });

  it("recognises a server rejecting an argument or a type", () => {
    expect(
      isUnsupportedDocumentError({
        graphQLErrors: [
          {
            message:
              'Unknown argument "setup" on field "Mutation.createLedger".',
            extensions: { code: "GRAPHQL_VALIDATION_FAILED" },
          },
        ],
      }),
    ).toBe(true);
    expect(
      isUnsupportedDocumentError(new Error('Unknown type "LedgerSetupInput".')),
    ).toBe(true);
    expect(
      isUnsupportedDocumentError(new Error("Network request failed")),
    ).toBe(false);
  });

  it("tells a preview the server cannot read from one it refused or could not reach", () => {
    const rejected = {
      message: 'Unknown type "LedgerSetupInput".',
      graphQLErrors: [
        {
          message: 'Unknown type "LedgerSetupInput".',
          extensions: { code: "GRAPHQL_VALIDATION_FAILED" },
        },
      ],
    };
    expect(previewFailureKind(rejected)).toBe("unsupported");
    expect(
      previewFailureKind({
        message: "bad",
        graphQLErrors: [{ extensions: { code: "BAD_USER_INPUT" } }],
      }),
    ).toBe("refused");
    expect(previewFailureKind(new Error("Received status code 502"))).toBe(
      "unreachable",
    );
  });

  it("says so in every language", () => {
    for (const locale of translationLocales()) {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const catalog = require(`../../../translations/${locale}`)[locale];
      expect(typeof catalog.createLedgerSetupUnsupported).toBe("string");
    }
  });
});
