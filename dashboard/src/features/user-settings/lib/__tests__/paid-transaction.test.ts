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
  amountPaid: 14388,
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
    ["nothing paid", { amountPaid: 0 }],
    ["an unknown amount", { amountPaid: null }],
    ["no currency", { currency: null }],
  ])("sends nothing for %s", async (_label, change) => {
    const { recordPaidTransaction } = await load();

    expect(recordPaidTransaction({ ...paid, ...change })).toBe(false);
    expect(mockTrack).not.toHaveBeenCalled();
  });
});
