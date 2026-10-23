import { recommendAccounts } from "../recommend-accounts";
import type { LLMClient } from "../llm-client";

// w21/281: the model's account suggestions were returned as-is, so a made-up
// `Expenses:Food:Groceries` reached clients (REST, GraphQL and MCP alike) and
// was written as an account the ledger never opened.
const OPEN = ["Assets:Bank:Checking", "Expenses:Dining"];
const TXN = {
  date: "2026-10-01",
  payee: "Cafe",
  description: "Lunch",
  amount: 12,
} as never;

function clientSuggesting(
  sourceAccount: string | null,
  targetAccount: string | null,
): LLMClient {
  return {
    generate: jest.fn().mockResolvedValue({
      output: { sourceAccount, targetAccount, confidence: 0.9, reasoning: "x" },
      usage: { inputTokens: 1, outputTokens: 1 },
    }),
  } as unknown as LLMClient;
}

describe("recommendAccounts", () => {
  it("keeps suggestions that are open accounts", async () => {
    const { recommendation } = await recommendAccounts(
      clientSuggesting("Assets:Bank:Checking", "Expenses:Dining"),
      TXN,
      OPEN,
    );
    expect(recommendation.sourceAccount).toBe("Assets:Bank:Checking");
    expect(recommendation.targetAccount).toBe("Expenses:Dining");
  });

  it("drops a suggestion the ledger does not have", async () => {
    const { recommendation } = await recommendAccounts(
      clientSuggesting("Assets:Cash", "Expenses:Food:Groceries"),
      TXN,
      OPEN,
    );
    expect(recommendation.sourceAccount).toBe(null);
    expect(recommendation.targetAccount).toBe(null);
  });

  it("drops every suggestion when the ledger lists no accounts", async () => {
    const { recommendation } = await recommendAccounts(
      clientSuggesting("Assets:Cash", "Expenses:Food:Groceries"),
      TXN,
      [],
    );
    expect(recommendation.sourceAccount).toBe(null);
    expect(recommendation.targetAccount).toBe(null);
  });

  it("drops only the unknown one", async () => {
    const { recommendation } = await recommendAccounts(
      clientSuggesting("Assets:Bank:Checking", "Expenses:Food:Groceries"),
      TXN,
      OPEN,
    );
    expect(recommendation.sourceAccount).toBe("Assets:Bank:Checking");
    expect(recommendation.targetAccount).toBe(null);
  });
});
