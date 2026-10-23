import type Stripe from "stripe";
import { BILLING_CLIENT_ID, SUBSCRIPTION_CONFIG } from "../../service/stripe";
import { changeAtRenewal, emailScheduledChange } from "../plan-change-email";
import type { ScheduledChangeNotice } from "../plan-change-schedule";

const PLANS = SUBSCRIPTION_CONFIG[BILLING_CLIENT_ID].plans;
const GROWTH_YEARLY = "price_1SyPdbEqsEqs2tLV7PJyWZed";
const GROWTH_MONTHLY = "price_1SyPdaEqsEqs2tLViLPUDoVi";
const PREMIUM_YEARLY = "price_1US5htEqsEqs2tLVENCzLaZB";
const START = 1_790_000_000;
const END = 1_823_774_400; // 2027-10-17T12:00:00Z
const at = new Date(END * 1000);

/** Growth yearly, scheduled to become `priceId` at END. */
const notice = (
  priceId = PREMIUM_YEARLY,
  previous: ScheduledChangeNotice["previous"] = null,
): ScheduledChangeNotice => ({
  subscriptionId: "sub_1",
  scheduleId: "sub_sched_1",
  currentPriceId: GROWTH_YEARLY,
  change: { priceId, effectiveAt: at },
  previous,
});

function setup() {
  const claimed = new Set<string>();
  const sentBillingEmail = {
    claim: jest.fn(async (_db: unknown, key: string) => {
      if (claimed.has(key)) return false;
      claimed.add(key);
      return true;
    }),
    release: jest.fn(async (_db: unknown, key: string) => {
      claimed.delete(key);
    }),
  };
  const getById = jest.fn(async () => ({ email: "subscriber@example.test" }));
  const sendMail = jest.fn(async () => undefined);
  const deps = {
    models: { user: { getById }, sentBillingEmail } as never,
    db: {} as never,
    sendgrid: { sendMail } as never,
  };
  const send = (kind: "scheduled" | "reminder", n = notice()) =>
    emailScheduledChange(deps, kind, "usr_1", BILLING_CLIENT_ID, n);
  return { send, sendMail, sentBillingEmail, getById };
}
const mailOf = (sendMail: jest.Mock, call = 0) =>
  sendMail.mock.calls[call][0] as {
    to: string;
    subject: string;
    text: string;
    html: string;
  };

describe("emailScheduledChange (PRFAQ005 question 17)", () => {
  it("confirms a scheduled downgrade with its date, the plans, what changes and how to keep the plan", async () => {
    const { send, sendMail } = setup();

    await expect(send("scheduled")).resolves.toBe("sent");

    const mail = mailOf(sendMail);
    expect(mail.to).toBe("subscriber@example.test");
    expect(mail.subject).toBe(
      "Your plan changes to Premium · Yearly on October 17, 2027",
    );
    expect(mail.text).toContain(
      "On October 17, 2027, your plan changes from Growth · Yearly to Premium · Yearly.",
    );
    expect(mail.text).toContain("- Ledgers: 20 → 5");
    expect(mail.text).toContain("- Collaborators per ledger: 10 → 5");
    // Billing settings, from the client's configuration.
    expect(mail.html).toContain('href="https://beancount.io/settings/billing"');
  });

  it("sends each kind once per change, whatever retries ask for", async () => {
    const { send, sendMail } = setup();

    await send("scheduled");
    await expect(send("scheduled")).resolves.toBe("already-sent");
    await send("reminder");
    await expect(send("reminder")).resolves.toBe("already-sent");

    expect(sendMail).toHaveBeenCalledTimes(2);
    expect(mailOf(sendMail, 1).subject).toMatch(/^Reminder: your plan changes/);
  });

  it("announces each new choice when a subscriber moves A, then B, then back to A", async () => {
    const { send, sendMail } = setup();
    const a = { priceId: PREMIUM_YEARLY, effectiveAt: at };
    const b = { priceId: GROWTH_MONTHLY, effectiveAt: at };

    await send("scheduled", notice(a.priceId, null));
    await send("scheduled", notice(b.priceId, a));
    await send("scheduled", notice(a.priceId, b));

    expect(sendMail).toHaveBeenCalledTimes(3);
    expect(mailOf(sendMail, 2).subject).toContain("Premium · Yearly");
  });

  it("claims nothing for a subscriber without an email, or when the lookup fails", async () => {
    const { send, sendMail, sentBillingEmail, getById } = setup();
    getById.mockResolvedValueOnce(null as never);
    await expect(send("reminder")).resolves.toBe("no-recipient");

    getById.mockRejectedValueOnce(new Error("database down"));
    await expect(send("reminder")).rejects.toThrow("database down");

    expect(sentBillingEmail.claim).not.toHaveBeenCalled();
    // The retry after the outage still sends.
    await expect(send("reminder")).resolves.toBe("sent");
    expect(sendMail).toHaveBeenCalledTimes(1);
  });

  it("gives the claim back when sending fails, so a retry sends it", async () => {
    const { send, sendMail, sentBillingEmail } = setup();
    sendMail.mockRejectedValueOnce(new Error("SendGrid down"));

    await expect(send("reminder")).rejects.toThrow("SendGrid down");
    expect(sentBillingEmail.release).toHaveBeenCalledTimes(1);
    await expect(send("reminder")).resolves.toBe("sent");
  });
});

describe("changeAtRenewal", () => {
  const subscription = (
    schedule: unknown,
    periodEnd = END,
  ): Stripe.Subscription =>
    ({
      id: "sub_1",
      schedule,
      items: {
        data: [
          // An add-on line first: the plan item is found by price, not position.
          { price: { id: "price_addon" }, current_period_end: periodEnd },
          { price: { id: GROWTH_YEARLY }, current_period_end: periodEnd },
        ],
      },
    }) as unknown as Stripe.Subscription;
  const schedule = (changeAt = END) => ({
    id: "sub_sched_1",
    status: "active",
    current_phase: { start_date: START, end_date: changeAt },
    phases: [
      { start_date: START, items: [{ price: GROWTH_YEARLY }] },
      { start_date: changeAt, items: [{ price: PREMIUM_YEARLY }] },
    ],
  });

  it("reads the change a schedule makes at the coming renewal", () => {
    expect(changeAtRenewal(subscription(schedule()), PLANS)).toEqual({
      subscriptionId: "sub_1",
      scheduleId: "sub_sched_1",
      currentPriceId: GROWTH_YEARLY,
      change: { priceId: PREMIUM_YEARLY, effectiveAt: at },
    });
  });

  it.each([
    ["nothing is scheduled", subscription(null)],
    [
      "the schedule was released",
      subscription({ ...schedule(), status: "released" }),
    ],
    // A change set for a later renewal is not this renewal's news.
    [
      "the change lands at a later renewal",
      subscription(schedule(END + 31_536_000)),
    ],
  ])("is null when %s", (_label, sub) => {
    expect(changeAtRenewal(sub, PLANS)).toBeNull();
  });
});
