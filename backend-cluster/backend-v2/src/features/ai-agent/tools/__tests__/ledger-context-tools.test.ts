import {
  executeCheckLedger,
  executeGetEntryContext,
  executeGetLedgerContext,
  executeListLedgers,
} from "../ledger-context-tools";
import type { Identity } from "@/server/api/identity";

/**
 * The four discovery reads (w2/m27:t003).
 *
 * Each tool wraps the same service call as its resource twin, so these tests
 * fake the services and assert the tool passes the call through unchanged —
 * the twin parity is structural (one service, two adapters), and the tests
 * pin the tool side of it.
 */

const IDENTITY: Identity = {
  userId: "user-123",
  method: "oauth",
  scopes: new Set(["ledger.read"]),
};
const LEDGER_ID = "alice/personal";

describe("executeListLedgers", () => {
  it("returns the workflow's catalog page, pin-restricted by the workflow", async () => {
    const ledgerWorkflow = {
      listLedgers: jest
        .fn()
        .mockResolvedValue([{ id: "alice/personal", name: "personal" }]),
    };
    const result = await executeListLedgers(
      { ledgerWorkflow: ledgerWorkflow as any, identity: IDENTITY },
      { page: 1, limit: 20 },
    );
    expect(result).toEqual({
      ok: true,
      result: [{ id: "alice/personal", name: "personal" }],
    });
    expect(ledgerWorkflow.listLedgers).toHaveBeenCalledWith({
      identity: IDENTITY,
      args: { page: 1, limit: 20 },
    });
  });
});

describe("executeCheckLedger", () => {
  const services = () => ({
    ledgerData: {
      getErrors: jest.fn().mockResolvedValue([
        {
          message: "Transaction does not balance",
          source: { filename: "main.bean", lineno: 12 },
        },
      ]),
      getEntriesCountPerType: jest
        .fn()
        .mockResolvedValue([{ type: "Transaction", count: 4 }]),
    },
    ledgerRepo: {
      getLatestCommit: jest.fn().mockResolvedValue({ sha: "abc123" }),
    },
  });

  it("returns the unbalanced error with file and line, plus counts and commit", async () => {
    const ctx = {
      services: services() as any,
      identity: IDENTITY,
      ledgerId: LEDGER_ID,
    };
    const result = await executeCheckLedger(ctx);
    expect(result).toEqual({
      ok: true,
      result: {
        errors: [
          {
            message: "Transaction does not balance",
            source: { filename: "main.bean", lineno: 12 },
          },
        ],
        entriesCount: [{ type: "Transaction", count: 4 }],
        latestCommit: { sha: "abc123" },
      },
    });
  });

  it("calls the same three service reads as the resource twins", async () => {
    const svc = services();
    await executeCheckLedger({
      services: svc as any,
      identity: IDENTITY,
      ledgerId: LEDGER_ID,
    });
    expect(svc.ledgerData.getErrors).toHaveBeenCalledWith({
      ledgerId: LEDGER_ID,
      identity: IDENTITY,
    });
    expect(svc.ledgerData.getEntriesCountPerType).toHaveBeenCalledWith({
      ledgerId: LEDGER_ID,
      identity: IDENTITY,
    });
    expect(svc.ledgerRepo.getLatestCommit).toHaveBeenCalledWith({
      ledgerId: LEDGER_ID,
      identity: IDENTITY,
    });
  });

  it("wraps a service rejection as ok:false rather than throwing", async () => {
    const svc = services();
    svc.ledgerData.getErrors.mockRejectedValue(new Error("forbidden"));
    const result = await executeCheckLedger({
      services: svc as any,
      identity: IDENTITY,
      ledgerId: LEDGER_ID,
    });
    expect(result.ok).toBe(false);
  });
});

describe("executeGetLedgerContext", () => {
  const services = () => ({
    ledgerData: {
      getAttributes: jest.fn().mockResolvedValue({ options: {} }),
      getCurrencies: jest.fn().mockResolvedValue(["USD", "EUR"]),
      getPayees: jest.fn().mockResolvedValue(["bakery", "grocer", "landlord"]),
      getYears: jest.fn().mockResolvedValue(["2024", "2025"]),
      getSourceFiles: jest.fn().mockResolvedValue(["main.bean"]),
    },
    ledgerAccount: {
      getAccounts: jest
        .fn()
        .mockResolvedValue(["Expenses:Food", "Assets:Cash"]),
    },
  });

  it("returns counts alongside truncated lists", async () => {
    const result = await executeGetLedgerContext(
      {
        services: services() as any,
        identity: IDENTITY,
        ledgerId: LEDGER_ID,
      },
      { payeeLimit: 2 },
    );
    expect(result).toEqual({
      ok: true,
      result: {
        attributes: { options: {} },
        accounts: ["Expenses:Food", "Assets:Cash"],
        currencies: ["USD", "EUR"],
        payees: ["bakery", "grocer"],
        payeeCount: 3,
        years: ["2024", "2025"],
        sourceFiles: ["main.bean"],
        sourceFileCount: 1,
      },
    });
  });

  /**
   * w6/013. The attributes document repeats the ledger's whole payee list, so
   * `payeeLimit: 1` still returned every payee inside `attributes`.
   */
  describe("payee limit inside the attributes document", () => {
    const payees = Array.from(
      { length: 60 },
      (_, i) => `payee ${String(i).padStart(2, "0")}`,
    );
    const attributes = () => ({
      accounts: ["Assets:Cash", "Expenses:Food"],
      tags: ["trip"],
      links: ["receipt-1"],
      years: ["2025"],
      currencies: ["USD"],
      payees: [...payees],
    });
    const run = async (input: { payeeLimit?: number }, full = attributes()) => {
      const svc = services();
      svc.ledgerData.getAttributes.mockResolvedValue(full);
      svc.ledgerData.getPayees.mockResolvedValue([...payees]);
      const result = await executeGetLedgerContext(
        { services: svc as any, identity: IDENTITY, ledgerId: LEDGER_ID },
        input,
      );
      if (!result.ok) throw new Error("Expected a context result");
      return result.result as {
        attributes: ReturnType<typeof attributes>;
        payees: string[];
        payeeCount: number;
      };
    };

    it("holds both payee lists to the requested limit and keeps the count", async () => {
      const result = await run({ payeeLimit: 1 });
      expect(result.payees).toEqual(["payee 00"]);
      expect(result.attributes.payees).toEqual(["payee 00"]);
      expect(result.payeeCount).toBe(60);
      // Every other attribute arrives untouched.
      const { payees: _payees, ...rest } = result.attributes;
      const { payees: _all, ...expected } = attributes();
      expect(rest).toEqual(expected);
    });

    it("applies the default limit of 50 to both lists", async () => {
      const result = await run({});
      expect(result.payees).toHaveLength(50);
      expect(result.attributes.payees).toEqual(payees.slice(0, 50));
    });

    it("returns every payee when the ledger has fewer than the limit", async () => {
      const result = await run({ payeeLimit: 500 });
      expect(result.attributes.payees).toEqual(payees);
      expect(result.payees).toEqual(payees);
    });

    it("projects a copy and leaves the service's document intact", async () => {
      const full = attributes();
      const result = await run({ payeeLimit: 2 }, full);
      expect(result.attributes).not.toBe(full);
      expect(full.payees).toHaveLength(60);
    });
  });

  it("reads open accounts for the ledger owner and name", async () => {
    const svc = services();
    await executeGetLedgerContext(
      { services: svc as any, identity: IDENTITY, ledgerId: LEDGER_ID },
      {},
    );
    expect(svc.ledgerAccount.getAccounts).toHaveBeenCalledWith(
      "alice",
      "personal",
      "open",
      IDENTITY,
    );
  });
});

describe("executeGetEntryContext", () => {
  it("passes the entry hash to the journal service untouched", async () => {
    const ledgerJournal = {
      getContext: jest.fn().mockResolvedValue({ hash: "deadbeef" }),
    };
    const result = await executeGetEntryContext(
      {
        services: { ledgerJournal } as any,
        identity: IDENTITY,
        ledgerId: LEDGER_ID,
      },
      { entryHash: "deadbeef" },
    );
    expect(result).toEqual({ ok: true, result: { hash: "deadbeef" } });
    expect(ledgerJournal.getContext).toHaveBeenCalledWith({
      ledgerId: LEDGER_ID,
      identity: IDENTITY,
      entryHash: "deadbeef",
    });
  });
});
