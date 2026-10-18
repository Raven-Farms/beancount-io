import { buildInstructions } from "../mcp-context";
import { PLAN_WORDING, STEERING_WORDING } from "./directory-wording";
import type { Identity } from "@/server/api/identity";

const base: Identity = {
  userId: "user-123",
  method: "oauth",
  scopes: new Set(["ledger.read", "ledger.write"]),
};

describe("buildInstructions", () => {
  it("states the pin for a pinned credential", () => {
    const text = buildInstructions({ ...base, ledgerScope: "alice/personal" });
    expect(text).toContain("alice/personal");
    expect(text).not.toMatch(/unpinned/i);
  });

  it("states the selection rule for an unpinned credential", () => {
    const text = buildInstructions(base);
    expect(text).toContain("ledger: owner/name");
    expect(text).toContain("listLedgers");
  });

  it("mentions validation, the URI grammar, and the BQL posting-row caveat", () => {
    for (const identity of [base, { ...base, ledgerScope: "alice/personal" }]) {
      const text = buildInstructions(identity);
      expect(text).toMatch(/checkLedger|validation/);
      expect(text).toContain("beancount://");
      expect(text).toMatch(/postings|LIMIT/);
    }
  });

  it("states that structured and text writes refuse new bean-check errors unless allowInvalid", () => {
    // Both write tools refuse a write that would break the ledger (w0/m2); a
    // session that only read "results include newErrors" would expect a
    // committed write to repair afterwards.
    for (const identity of [base, { ...base, ledgerScope: "alice/personal" }]) {
      const text = buildInstructions(identity);
      expect(text).toMatch(
        /`addLedgerEntries` and `appendLedgerText` refuse writes that add bean-check errors unless `allowInvalid: true`/,
      );
    }
  });

  it("stays under 1,500 characters; it is paid on every session", () => {
    expect(buildInstructions(base).length).toBeLessThan(1500);
    expect(
      buildInstructions({ ...base, ledgerScope: "alice/personal" }).length,
    ).toBeLessThan(1500);
  });

  it("describes the server and never directs the model or mentions plans", () => {
    // Both connector directories reject text that steers the model or
    // promotes upgrades (ADR 019, 2026-10-09 amendment).
    for (const identity of [base, { ...base, ledgerScope: "alice/personal" }]) {
      const text = buildInstructions(identity);
      expect(text).not.toMatch(STEERING_WORDING);
      expect(text).not.toMatch(PLAN_WORDING);
    }
  });
});
