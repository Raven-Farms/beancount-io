import { splitCommitMessage } from "../formatting";

// Git messages end in a newline and wrap their bodies near 72 columns. Shown
// raw, the trailing newline became a blank second line in Recent Changes and
// the body kept its hard wraps in commit detail (w0/032).
describe("splitCommitMessage", () => {
  it("drops the trailing newline git adds to a one-line message", () => {
    expect(
      splitCommitMessage("verify: unaffected ledger still pushes\n"),
    ).toEqual({
      subject: "verify: unaffected ledger still pushes",
      body: null,
    });
  });

  it("splits the subject from a body after the blank line", () => {
    expect(
      splitCommitMessage("Add main.bean\n\nSeed the ledger with opens.\n"),
    ).toEqual({
      subject: "Add main.bean",
      body: "Seed the ledger with opens.",
    });
  });

  it("treats CRLF and CR line endings like LF", () => {
    expect(splitCommitMessage("Subject\r\n\r\nBody line\r\n")).toEqual({
      subject: "Subject",
      body: "Body line",
    });
    expect(splitCommitMessage("Subject\r\rBody line\r")).toEqual({
      subject: "Subject",
      body: "Body line",
    });
  });

  it("returns an empty subject and no body for an empty message", () => {
    for (const message of ["", "\n", "  \n\t\n"]) {
      expect(splitCommitMessage(message)).toEqual({ subject: "", body: null });
    }
  });

  it("starts at the first non-blank line and trims the subject", () => {
    expect(splitCommitMessage("\n\n  Rebuild ledger  \n")).toEqual({
      subject: "Rebuild ledger",
      body: null,
    });
  });

  it("joins hard-wrapped lines so a paragraph reflows to the screen", () => {
    const { body } = splitCommitMessage(
      "Rebuild as a trader ledger\n\n" +
        "Because upstream Beancount\n" +
        "does not fetch URLs and\n" +
        "the bea CLI loader is still in flight, prices are managed.\n",
    );
    expect(body).toBe(
      "Because upstream Beancount does not fetch URLs and the bea CLI " +
        "loader is still in flight, prices are managed.",
    );
  });

  it("keeps paragraph breaks between reflowed paragraphs", () => {
    const { body } = splitCommitMessage(
      "Subject\n\nFirst paragraph\nwraps here.\n\n\nSecond paragraph\nwraps too.\n",
    );
    expect(body).toBe(
      "First paragraph wraps here.\n\nSecond paragraph wraps too.",
    );
  });

  it("starts each list item on its own row and joins its wrapped lines", () => {
    const { body } = splitCommitMessage(
      "Subject\n\nThree corrections:\n\n" +
        "- inferred_tolerance_default was 0.01, which gave every crypto\n" +
        "  quantity a 0.01 tolerance.\n" +
        "- add prices that\nspan two lines\n" +
        "  - a nested item\n" +
        "1. first\n2) second\n",
    );
    expect(body).toBe(
      "Three corrections:\n\n" +
        "- inferred_tolerance_default was 0.01, which gave every crypto quantity a 0.01 tolerance.\n" +
        "- add prices that span two lines\n" +
        "  - a nested item\n" +
        "1. first\n2) second",
    );
  });

  it("keeps indented code lines as written, and prose off them", () => {
    const { body } = splitCommitMessage(
      "Subject\n\nPrices now come from one include:\n" +
        '    include "prices/BTC-USD"\n' +
        "    bea check main.bean\n" +
        "and nothing else.\n",
    );
    expect(body).toBe(
      "Prices now come from one include:\n" +
        '    include "prices/BTC-USD"\n' +
        "    bea check main.bean\n" +
        "and nothing else.",
    );
  });

  it("keeps a trailer block one trailer per line", () => {
    const { body } = splitCommitMessage(
      "Subject\n\nBody.\n\nSigned-off-by: A Person <a@example.com>\nCo-Authored-By: B Person <b@example.com>\n",
    );
    expect(body).toBe(
      "Body.\n\nSigned-off-by: A Person <a@example.com>\nCo-Authored-By: B Person <b@example.com>",
    );
  });
});
