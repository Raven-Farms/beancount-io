import type Stripe from "stripe";
import { BILLING_CLIENT_ID, SUBSCRIPTION_CONFIG } from "../../service/stripe";
import {
  emailFailedRenewal,
  emailRenewalReminder,
  failedRenewal,
  invoicePlan,
  type FailedRenewal,
} from "../renewal-email";

const PLANS = SUBSCRIPTION_CONFIG[BILLING_CLIENT_ID].plans;
const PREMIUM_YEARLY = "price_1US5htEqsEqs2tLVENCzLaZB";
const PREMIUM_MONTHLY = "price_1RrSOGEqsEqs2tLVFnyB34qG";
const RENEWAL = 1_823_774_400; // 2027-10-17T12:00:00Z
const NEXT_ATTEMPT = 1_792_670_400; // 2026-10-22T12:00:00Z
const PREMIUM_YEARLY_PLAN = PLANS.find(
  (plan) => plan.priceId === PREMIUM_YEARLY,
)!;

const invoice = (overrides: Partial<Stripe.Invoice> = {}) =>
  ({
    id: "in_1",
    billing_reason: "subscription_cycle",
    attempt_count: 1,
    next_payment_attempt: NEXT_ATTEMPT,
    amount_due: 14388,
    currency: "usd",
    lines: {
      data: [{ pricing: { price_details: { price: PREMIUM_YEARLY } } }],
    },
    ...overrides,
  }) as unknown as Stripe.Invoice;

const subscription = (
  priceId = PREMIUM_YEARLY,
  overrides: Partial<Stripe.Subscription> = {},
  periodEnd = RENEWAL,
) =>
  ({
    id: "sub_1",
    cancel_at_period_end: false,
    items: {
      data: [{ price: { id: priceId }, current_period_end: periodEnd }],
    },
    ...overrides,
  }) as unknown as Stripe.Subscription;

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
  const fail = (failure: FailedRenewal, inv = invoice()) =>
    emailFailedRenewal(
      deps,
      "usr_1",
      BILLING_CLIENT_ID,
      inv,
      PREMIUM_YEARLY_PLAN,
      failure,
    );
  const remind = (sub = subscription(), inv = invoice()) =>
    emailRenewalReminder(deps, "usr_1", BILLING_CLIENT_ID, inv, sub);
  return { fail, remind, sendMail, sentBillingEmail, getById };
}
const mailOf = (sendMail: jest.Mock, call = 0) =>
  sendMail.mock.calls[call][0] as {
    to: string;
    subject: string;
    text: string;
    html: string;
  };
const FIRST: FailedRenewal = {
  invoiceId: "in_1",
  kind: "failed",
  nextAttemptAt: new Date(NEXT_ATTEMPT * 1000),
};

describe("invoicePlan", () => {
  it("finds our plan on an invoice, and none on another product's", () => {
    expect(invoicePlan(invoice(), PLANS)?.priceId).toBe(PREMIUM_YEARLY);
    expect(
      invoicePlan(
        invoice({
          lines: {
            data: [{ pricing: { price_details: { price: "price_other" } } }],
          } as never,
        }),
        PLANS,
      ),
    ).toBeUndefined();
  });
});

describe("failedRenewal", () => {
  it("calls for the first-failure email after a renewal's first attempt", () => {
    expect(failedRenewal(invoice())).toEqual(FIRST);
  });

  it("calls for the final notice once no retry is left, whatever the attempt", () => {
    for (const attempt_count of [1, 5]) {
      expect(
        failedRenewal(invoice({ attempt_count, next_payment_attempt: null })),
      ).toEqual({ invoiceId: "in_1", kind: "final" });
    }
  });

  it("calls for nothing on the retries in between", () => {
    expect(failedRenewal(invoice({ attempt_count: 2 }))).toBeNull();
    expect(failedRenewal(invoice({ attempt_count: 3 }))).toBeNull();
  });

  it("calls for nothing on a charge that is not a renewal", () => {
    for (const billing_reason of [
      "subscription_update",
      "subscription_create",
      "manual",
    ] as const) {
      expect(failedRenewal(invoice({ billing_reason }))).toBeNull();
    }
  });
});

describe("emailFailedRenewal", () => {
  it("says what failed, that we retry and when, and links to Billing", async () => {
    const { fail, sendMail } = setup();

    await expect(fail(FIRST)).resolves.toBe("sent");

    const mail = mailOf(sendMail);
    expect(mail.to).toBe("subscriber@example.test");
    expect(mail.subject).toBe(
      "Your Premium · Yearly renewal didn't go through",
    );
    expect(mail.text).toContain(
      "We couldn't charge $143.88 for your Premium · Yearly renewal.",
    );
    expect(mail.text).toContain("the next attempt is on October 22, 2026");
    expect(mail.html).toContain('href="https://beancount.io/settings/billing"');
    expect(mail.html).toContain("Update your card");
  });

  it("says plainly when the plan has ended", async () => {
    const { fail, sendMail } = setup();

    await fail({ invoiceId: "in_1", kind: "final" });

    const mail = mailOf(sendMail);
    expect(mail.subject).toBe("Your Premium · Yearly plan has ended");
    expect(mail.text).toContain("your account is on the Free plan");
    expect(mail.text).toContain("Nothing is deleted.");
  });

  it("sends each kind once per invoice, whatever Stripe redelivers", async () => {
    const { fail, sendMail } = setup();

    await fail(FIRST);
    await expect(fail(FIRST)).resolves.toBe("already-sent");
    await fail({ invoiceId: "in_1", kind: "final" });

    expect(sendMail).toHaveBeenCalledTimes(2);
  });

  it("gives the claim back when the send fails, so a redelivery can send it", async () => {
    const { fail, sendMail, sentBillingEmail } = setup();
    sendMail.mockRejectedValueOnce(new Error("SendGrid down"));

    await expect(fail(FIRST)).rejects.toThrow("SendGrid down");
    expect(sentBillingEmail.release).toHaveBeenCalledWith(
      {},
      "renewal-failed:in_1",
    );
    await expect(fail(FIRST)).resolves.toBe("sent");
  });

  it("sends nothing to a user without an email address", async () => {
    const { fail, sendMail, getById, sentBillingEmail } = setup();
    getById.mockResolvedValueOnce({ email: "" });

    await expect(fail(FIRST)).resolves.toBe("no-recipient");
    expect(sendMail).not.toHaveBeenCalled();
    expect(sentBillingEmail.claim).not.toHaveBeenCalled();
  });
});

describe("emailRenewalReminder", () => {
  it("reminds a yearly subscriber of the renewal date and charge", async () => {
    const { remind, sendMail } = setup();

    await expect(remind()).resolves.toBe("sent");

    const mail = mailOf(sendMail);
    expect(mail.subject).toBe(
      "Your Premium · Yearly plan renews on October 17, 2027",
    );
    expect(mail.text).toContain(
      "On October 17, 2027, your Premium · Yearly plan renews for another year, and $143.88 is charged",
    );
    expect(mail.html).toContain('href="https://beancount.io/settings/billing"');
  });

  it("charges what the upcoming invoice says, discounts included", async () => {
    const { remind, sendMail } = setup();

    await remind(subscription(), invoice({ amount_due: 7194 }));

    expect(mailOf(sendMail).text).toContain("$71.94 is charged");
  });

  it("reminds nobody on a monthly plan, a plan set to end, or a renewal that charges nothing", async () => {
    const { remind, sendMail } = setup();

    await expect(remind(subscription(PREMIUM_MONTHLY))).resolves.toBe(
      "not-applicable",
    );
    await expect(
      remind(subscription(PREMIUM_YEARLY, { cancel_at_period_end: true })),
    ).resolves.toBe("not-applicable");
    await expect(
      remind(subscription(), invoice({ amount_due: 0 })),
    ).resolves.toBe("not-applicable");
    await expect(remind(subscription("price_other"))).resolves.toBe(
      "not-applicable",
    );
    expect(sendMail).not.toHaveBeenCalled();
  });

  it("reminds once per renewal, and again at next year's", async () => {
    const { remind, sendMail } = setup();

    await remind();
    await expect(remind()).resolves.toBe("already-sent");
    await remind(subscription(PREMIUM_YEARLY, {}, RENEWAL + 31_536_000));

    expect(sendMail).toHaveBeenCalledTimes(2);
  });
});
