import { beforeEach, describe, expect, it, vi } from "vitest";
import { cyclePrice } from "@/features/user-settings/pages/general/stripe-config";

const PREMIUM_YEARLY_PRICE_ID = cyclePrice("premium", "yearly").priceId;

const { mockTrack } = vi.hoisted(() => ({ mockTrack: vi.fn() }));
vi.mock("@/common/analytics", () => ({ track: mockTrack }));

const load = async () => {
  vi.resetModules();
  return import("../paid-transaction");
};

const paid = {
  invoiceId: "in_first",
  amount: 14388,
  currency: "usd",
  priceId: PREMIUM_YEARLY_PRICE_ID,
};

/** A working store: the global test setup's localStorage keeps nothing. */
function memoryStorage(): Storage {
  const items = new Map<string, string>();
  return {
    getItem: (key) => items.get(key) ?? null,
    setItem: (key, value) => void items.set(key, value),
    removeItem: (key) => void items.delete(key),
    clear: () => items.clear(),
    key: (index) => [...items.keys()][index] ?? null,
    get length() {
      return items.size;
    },
  };
}

beforeEach(() => {
  mockTrack.mockClear();
  vi.stubGlobal("localStorage", memoryStorage());
});

describe("recordPaidTransaction", () => {
  it("sends one GA4 purchase in major units with the plan as its item", async () => {
    const { recordPaidTransaction } = await load();

    expect(recordPaidTransaction(paid)).toBe(true);

    expect(mockTrack).toHaveBeenCalledTimes(1);
    expect(mockTrack).toHaveBeenCalledWith("purchase", {
      transaction_id: "in_first",
      value: 143.88,
      currency: "USD",
      items: [
        {
          item_id: PREMIUM_YEARLY_PRICE_ID,
          item_name: "premium",
          item_variant: "year",
          price: 143.88,
          quantity: 1,
        },
      ],
    });
  });

  it("counts an invoice once on this browser, across reloads", async () => {
    expect((await load()).recordPaidTransaction(paid)).toBe(true);
    // A fresh module is a reload: only storage remembers.
    expect((await load()).recordPaidTransaction(paid)).toBe(false);
    expect(mockTrack).toHaveBeenCalledTimes(1);
  });

  it("still counts once per page load when storage is unavailable", async () => {
    const { recordPaidTransaction } = await load();
    vi.stubGlobal("localStorage", {
      ...memoryStorage(),
      getItem: () => {
        throw new Error("storage disabled");
      },
    });

    expect(recordPaidTransaction(paid)).toBe(true);
    expect(recordPaidTransaction(paid)).toBe(false);
    expect(mockTrack).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["no invoice", { invoiceId: null }],
    ["an empty invoice id", { invoiceId: "" }],
    ["nothing paid", { amount: 0 }],
    ["an unknown amount", { amount: null }],
    ["no currency", { currency: null }],
  ])("sends nothing for %s", async (_label, change) => {
    const { recordPaidTransaction } = await load();

    expect(recordPaidTransaction({ ...paid, ...change })).toBe(false);
    expect(mockTrack).not.toHaveBeenCalled();
  });

  it("reports no billing cycle for a price this app does not know", async () => {
    const { recordPaidTransaction } = await load();

    recordPaidTransaction({
      ...paid,
      invoiceId: "in_unknown",
      priceId: "price_unknown",
    });

    const [, params] = mockTrack.mock.calls[0];
    expect(params.items[0]).toEqual({
      item_id: "price_unknown",
      item_name: "unknown",
      price: 143.88,
      quantity: 1,
    });
  });

  it("converts a zero-decimal currency without dividing by 100", async () => {
    const { recordPaidTransaction } = await load();

    recordPaidTransaction({
      ...paid,
      invoiceId: "in_yen",
      amount: 1500,
      currency: "jpy",
    });

    expect(mockTrack).toHaveBeenCalledWith(
      "purchase",
      expect.objectContaining({ value: 1500, currency: "JPY" }),
    );
  });
});

describe("isFreshCheckoutInvoice", () => {
  const now = Date.parse("2026-10-20T12:00:00Z");
  const hours = (h: number) => new Date(now - h * 60 * 60 * 1000);

  it.each([
    ["just created", hours(0), true],
    ["created 23 hours ago", hours(23), true],
    ["created 25 hours ago, an old bookmark", hours(25), false],
    ["dated in the future, a skewed clock", hours(-1), false],
  ])("treats an invoice %s as %s", async (_label, created, fresh) => {
    const { isFreshCheckoutInvoice } = await load();

    expect(isFreshCheckoutInvoice(created.toISOString(), now)).toBe(fresh);
  });
});
