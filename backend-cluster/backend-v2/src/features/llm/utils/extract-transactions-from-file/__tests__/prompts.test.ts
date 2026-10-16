import {
  buildTransactionFileAnalysisPrompt,
  buildTransactionImageAnalysisPrompt,
  buildTransactionSystemPrompt,
  buildTransactionTextAnalysisPrompt,
} from "../prompts";

const source = [
  "Date;Description;Payee;Amount",
  "2026-10-01;  QA Synthetic Gehalt  ;QA Synthetic Payroll;1000",
  "2026-10-02;;QA Synthetic Grocer;-23.1",
  "2026-10-03;Bäckerei  №42 — 食費;QA Synthetic Bakery;-5.2",
].join("\n");

describe("transaction extraction prompt grounding contract", () => {
  it.each(["csv", "ofx", "qif", "txt", "pdf", "image"])(
    "%s requires source wording rather than generated transaction prose",
    (format) => {
      const prompt = buildTransactionSystemPrompt(format);
      expect(prompt).toContain(
        "Copy the source memo/description exactly as written; trim leading and trailing whitespace only.",
      );
      expect(prompt).toContain(
        'If no source memo/description is present, set description to "".',
      );
      expect(prompt).toContain(
        "Do not translate, paraphrase, summarize, truncate, or invent context.",
      );
      expect(prompt).toContain("do not translate payee names");
      expect(prompt).not.toMatch(
        /Provide useful context|Meaningful description with context|Keep it concise \(under 100 chars\)/,
      );
    },
  );

  it("pins source fidelity and the limited non-plaintext bill exception", () => {
    const prompt = buildTransactionSystemPrompt("csv");
    const descriptionRules = prompt.slice(
      prompt.indexOf("## DESCRIPTION FIELD"),
      prompt.indexOf("## SKIP NON-TRANSACTIONS"),
    );
    expect(descriptionRules).toMatchInlineSnapshot(`
"## DESCRIPTION FIELD

STATEMENT rows and all plaintext documents, including plaintext BILL documents:
- Copy the source memo/description exactly as written; trim leading and trailing whitespace only.
- Preserve the original language, spelling, punctuation, capitalization, internal spacing and reference numbers.
- Do not translate, paraphrase, summarize, truncate, or invent context.
- Do not add text from the payee, amount, filename, other rows, or inferred transaction purpose.
- If no source memo/description is present, set description to "".
- For a plaintext BILL, use only an explicitly printed bill-level memo/description; otherwise use "".
- A payee alone is not a memo; do not infer a description from the merchant or counterparty.
- Keep "Gehalt" unchanged; never replace it with "Salary payment".

BILL summary exception — image/PDF attachment without plaintext ONLY:
- Return one transaction for the bill total. Its description may summarize only services and billing periods actually printed in the source, in the original language.
- This exception never applies to STATEMENT rows or any document supplied as plaintext.

"
`);
  });

  it("aggregates bills without giving every bill permission to synthesize a description", () => {
    const prompt = buildTransactionSystemPrompt("txt");
    const classification = prompt.slice(
      prompt.indexOf("**BILL**"),
      prompt.indexOf("## OUTPUT FORMAT"),
    );
    expect(classification).toContain("Return exactly ONE transaction");
    expect(classification).toContain("DO NOT split by line item");
    expect(classification).toContain(
      "follow the DESCRIPTION FIELD rules below",
    );
    expect(classification).not.toMatch(
      /concise service summary|ONE summarized transaction/,
    );
  });

  it("keeps OFX NAME and MEMO separate instead of filling a missing memo from the payee", () => {
    const prompt = buildTransactionSystemPrompt("ofx");
    expect(prompt).toContain("<NAME> = payee");
    expect(prompt).toContain("<MEMO> = description");
    expect(prompt).toContain("Keep NAME and MEMO separate");
    expect(prompt).not.toContain("Combine NAME and MEMO intelligently");
  });

  it("carries multilingual source text unchanged and forbids summaries even for plaintext bills", () => {
    const prompt = buildTransactionTextAnalysisPrompt("csv", source);
    expect(prompt).toContain(source);
    expect(prompt).toContain("This message supplies plaintext");
    expect(prompt).toContain("including a single BILL transaction");
    expect(prompt).toContain("Do not summarize plaintext bills");
    expect(prompt).toContain('If it is absent, return description ""');
    expect(prompt).not.toContain("No plaintext is supplied");
  });

  it.each([
    ["image", buildTransactionImageAnalysisPrompt],
    ["pdf", () => buildTransactionFileAnalysisPrompt("pdf")],
  ] as const)(
    "limits the %s summary exception to a bill without plaintext",
    (_format, build) => {
      const prompt = build();
      expect(prompt).toContain("No plaintext is supplied");
      expect(prompt).toContain("Only for an image/PDF BILL");
      expect(prompt).toContain("printed details in the original language");
      expect(prompt).toContain(
        "STATEMENT descriptions must still be copied verbatim",
      );
    },
  );

  it.each([
    ["text", () => buildTransactionTextAnalysisPrompt("csv", source)],
    ["image", buildTransactionImageAnalysisPrompt],
    ["file", () => buildTransactionFileAnalysisPrompt("pdf")],
  ] as const)(
    "keeps payee normalization distinct from translation in the %s user prompt",
    (_mode, build) => {
      expect(build()).toContain("do not translate payee names");
      expect(build()).not.toContain("Meaningful description with context");
    },
  );
});
