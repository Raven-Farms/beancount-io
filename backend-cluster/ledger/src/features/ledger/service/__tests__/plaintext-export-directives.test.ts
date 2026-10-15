import type { DirectiveJson } from "@rustledger/wasm";
import { plaintextExportDirectives } from "@/features/ledger/service/ledger-journal-service";

const txn = (flag: string, narration: string): DirectiveJson =>
  ({
    type: "transaction",
    date: "2016-01-01",
    flag,
    narration,
    tags: [],
    links: [],
    meta: {},
    postings: [],
  }) as unknown as DirectiveJson;

const stream = [
  { type: "open", date: "2015-01-01", account: "Assets:Cash" },
  txn("S", "Opening balance for 'Assets:Brokerage' (Summarization)"),
  { type: "pad", date: "2016-03-01", account: "Assets:Cash" },
  txn("P", "(Padding inserted for Balance of 800 USD for difference 300 USD)"),
  { type: "balance", date: "2016-03-02", account: "Assets:Cash" },
  txn("*", "Sell part of the pre-window lot"),
  txn("!", "Pending"),
  txn("T", "Transfer balance"),
  txn("C", "Conversion for (-80 USD)"),
  { type: "price", date: "2016-04-01", currency: "VHT" },
] as unknown as DirectiveJson[];

const describeEach = (directives: DirectiveJson[]) =>
  directives.map((directive) =>
    directive.type === "transaction"
      ? `${directive.flag} ${directive.narration}`
      : directive.type,
  );

describe("plaintextExportDirectives", () => {
  it("keeps a time window's opening summaries so the export loads on its own", () => {
    expect(
      describeEach(plaintextExportDirectives(stream, { windowed: true })),
    ).toEqual([
      "S Opening balance for 'Assets:Brokerage' (Summarization)",
      "pad",
      "balance",
      "* Sell part of the pre-window lot",
      "! Pending",
    ]);
  });

  it("emits pads but never the synthetic padding, transfer or conversion entries", () => {
    expect(
      describeEach(plaintextExportDirectives(stream, { windowed: false })),
    ).toEqual([
      "pad",
      "balance",
      "* Sell part of the pre-window lot",
      "! Pending",
    ]);
  });
});
