import {
  applyUserRepair,
  fingerprint,
  planUserRepair,
  rollbackRepair,
  type BindingSnapshot,
  type RepairStore,
} from "../reconcile-billing-core";
const row = (
  id: string,
  clientId = "beancount-web-prod",
  period: string | null = null,
): BindingSnapshot => ({
  id,
  userId: "u",
  clientId,
  stripeCustomerId: `cus_${id}`,
  period,
  version: "v1",
});
const load = jest.fn(
  async (binding: BindingSnapshot) =>
    [
      {
        id: "sub_synthetic",
        clientId: binding.clientId,
        customer: binding.stripeCustomerId,
        livemode: true,
        status: "active",
        items: {
          data: [
            {
              price: { id: "price_1SyPdcEqsEqs2tLVCWEgU1PZ" },
              current_period_end: 2000000000,
            },
          ],
        },
      },
    ] as any,
);
afterEach(() => jest.clearAllMocks());
describe("preview/apply/rollback reconciliation", () => {
  it("previews mixed histories without writes, preserves test history and sets only verified live periods", async () => {
    const rows = [
      row("old", "beancount-web-dev", "2038-01-01T00:00:00.000Z"),
      row("live"),
    ];
    const initial = JSON.stringify(rows);
    const plan = await planUserRepair("u", rows, load);
    expect(plan.classification).toBe("mixed");
    expect(plan.changes).toEqual([
      { id: "live", period: "2033-05-18T03:33:20.000Z" },
      { id: "old", period: null },
    ]);
    expect(JSON.stringify(rows)).toBe(initial);
    expect(load).toHaveBeenCalledTimes(1);
  });
  it("applies transactionally with a prior rollback record; second preview is a no-op and rollback restores values", async () => {
    let rows = [
      row("live"),
      row("old", "beancount-web-dev", "2038-01-01T00:00:00.000Z"),
    ];
    const original = structuredClone(rows);
    const events: string[] = [];
    const store: RepairStore = {
      read: async () => structuredClone(rows),
      compareAndSet: async (repair) => {
        expect(fingerprint(rows)).toBe(fingerprint(repair.before));
        events.push("commit");
        rows = rows.map((row) => ({
          ...row,
          period:
            repair.changes.find((c) => c.id === row.id)?.period ??
            (repair.changes.some((c) => c.id === row.id) ? null : row.period),
        }));
        return rows;
      },
    };
    const plan = await planUserRepair("u", rows, load);
    await applyUserRepair(plan, store, load, async () => {
      events.push("journal");
    });
    expect(events).toEqual(["journal", "commit"]);
    expect((await planUserRepair("u", rows, load)).changes).toEqual([]);
    await store.compareAndSet(rollbackRepair(plan, structuredClone(rows)));
    expect(rows).toEqual(original);
  });
  it("rejects concurrent row/provider changes and performs zero writes on provider failure", async () => {
    const rows = [row("live")];
    const plan = await planUserRepair("u", rows, load);
    const commit = jest.fn();
    const journal = jest.fn();
    await expect(
      applyUserRepair(
        plan,
        {
          read: async () => [
            row("live", "beancount-web-prod", "2038-01-01T00:00:00.000Z"),
          ],
          compareAndSet: commit,
        },
        load,
        journal,
      ),
    ).rejects.toThrow("changed since preview");
    await expect(
      applyUserRepair(
        plan,
        { read: async () => rows, compareAndSet: commit },
        async () => {
          throw new Error("outage");
        },
        journal,
      ),
    ).rejects.toThrow("outage");
    expect(commit).not.toHaveBeenCalled();
    expect(journal).not.toHaveBeenCalled();
  });
  it("leaves no-history/test-only unchanged and marks missing/ambiguous ownership unresolved", async () => {
    expect((await planUserRepair("u", [], load)).classification).toBe(
      "no-history",
    );
    expect(
      (await planUserRepair("u", [row("old", "beancount-web-dev")], load))
        .classification,
    ).toBe("test-only");
    expect(
      (await planUserRepair("u", [row("one"), row("two")], load))
        .classification,
    ).toBe("unresolved");
    expect(
      (
        await planUserRepair("u", [row("live")], async () => [
          { ...(await load(row("live")))[0], customer: "cus_other" },
        ])
      ).classification,
    ).toBe("unresolved");
    expect(load).toHaveBeenCalledTimes(1);
  });
});
