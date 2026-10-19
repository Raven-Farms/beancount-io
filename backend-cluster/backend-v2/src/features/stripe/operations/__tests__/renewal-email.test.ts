import type Stripe from "stripe";
import { BILLING_CLIENT_ID, SUBSCRIPTION_CONFIG } from "../../service/stripe";
import {
  awaitsAuthentication,
  emailFailedRenewal,
  emailPlanEnded,
  emailRenewalReminder,
  invoicePlan,
  isFirstFailedRenewal,
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
  }) as unknown as Stripe.Invoice & { id: string };

const subscription = (
  priceId = PREMIUM_YEARLY,
  overrides: Partial<Stripe.Subscription> = {},
  periodEnd = RENEWAL,
) =>
  ({
    id: "sub_1",
    status: "active",
    cancel_at: null,
    cancel_at_period_end: false,
    items: {
      data: [{ price: { id: priceId }, current_period_end: periodEnd }],
    },
    ...overrides,
  }) as unknown as Stripe.Subscription;

/** A subscription Stripe canceled for `reason`. */
const canceled = (
  reason: Stripe.Subscription.CancellationDetails.Reason | null,
  overrides: Partial<Stripe.Subscription> = {},
  priceId = PREMIUM_YEARLY,
) =>
  subscription(priceId, {
    status: "canceled",
    cancellation_details: { comment: null, feedback: null, reason },
    ...overrides,
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
  const fail = (inv = invoice()) =>
    emailFailedRenewal(
      deps,
      "usr_1",
      BILLING_CLIENT_ID,
      inv,
      PREMIUM_YEARLY_PLAN,
    );
  const end = (sub = canceled("payment_failed")) =>
    emailPlanEnded(deps, "usr_1", BILLING_CLIENT_ID, sub);
  const remind = (sub = subscription(), inv = invoice()) =>
    emailRenewalReminder(deps, "usr_1", BILLING_CLIENT_ID, inv, sub);
  return { fail, end, remind, sendMail, sentBillingEmail, getById };
}
const mailOf = (sendMail: jest.Mock, call = 0) =>
  sendMail.mock.calls[call][0] as {
    to: string;
    subject: string;
    text: string;
    html: string;
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

describe("isFirstFailedRenewal", () => {
  it("is a renewal's first failed charge, whether or not a retry is scheduled", () => {
    expect(isFirstFailedRenewal(invoice())).toBe(true);
    expect(isFirstFailedRenewal(invoice({ next_payment_attempt: null }))).toBe(
      true,
    );
  });

  it("is not a retry, whether or not another follows", () => {
    for (const attempt_count of [2, 3, 5]) {
      expect(isFirstFailedRenewal(invoice({ attempt_count }))).toBe(false);
      expect(
        isFirstFailedRenewal(
          invoice({ attempt_count, next_payment_attempt: null }),
        ),
      ).toBe(false);
    }
  });

  it("is not a charge that is not a renewal", () => {
    for (const billing_reason of [
      "subscription_update",
      "subscription_create",
      "manual",
    ] as const) {
      expect(isFirstFailedRenewal(invoice({ billing_reason }))).toBe(false);
    }
  });
});

describe("awaitsAuthentication", () => {
  const stripeWith = (list: jest.Mock) =>
    ({ invoicePayments: { list } }) as unknown as Stripe;
  const payments = (...intents: unknown[]) =>
    jest.fn(async () => ({
      data: intents.map((payment_intent) => ({ payment: { payment_intent } })),
    }));

  it("reads the invoice's payments with their payment intents", async () => {
    const list = payments();

    await awaitsAuthentication(stripeWith(list), "in_1");

    expect(list).toHaveBeenCalledWith({
      invoice: "in_1",
      expand: ["data.payment.payment_intent"],
    });
  });

  it("is true while the bank waits for the customer", async () => {
    for (const intent of [
      { status: "requires_action", last_payment_error: null },
      {
        status: "requires_payment_method",
        last_payment_error: { code: "authentication_required" },
      },
    ]) {
      await expect(
        awaitsAuthentication(stripeWith(payments(intent)), "in_1"),
      ).resolves.toBe(true);
    }
  });

  it("is false for a decline, or an intent it cannot see", async () => {
    for (const intent of [
      {
        status: "requires_payment_method",
        last_payment_error: { code: "card_declined" },
      },
      "pi_unexpanded",
    ]) {
      await expect(
        awaitsAuthentication(stripeWith(payments(intent)), "in_1"),
      ).resolves.toBe(false);
    }
  });

  it("is false when Stripe cannot say, so the email still goes", async () => {
    const list = jest.fn(async () => {
      throw new Error("Stripe unavailable");
    });

    await expect(awaitsAuthentication(stripeWith(list), "in_1")).resolves.toBe(
      false,
    );
  });
});

describe("emailFailedRenewal", () => {
  it("says what failed, that we retry and when, and links to Billing", async () => {
    const { fail, sendMail } = setup();

    await expect(fail()).resolves.toBe("sent");

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

  it("promises no retry when Stripe has scheduled none", async () => {
    const { fail, sendMail } = setup();

    await fail(invoice({ next_payment_attempt: null }));

    const { text } = mailOf(sendMail);
    expect(text).toContain("so we can collect it and keep your plan");
    expect(text).not.toContain("next attempt");
  });

  it("sends once per invoice, whatever Stripe redelivers", async () => {
    const { fail, sendMail } = setup();

    await fail();
    await expect(fail()).resolves.toBe("already-sent");
    await fail(invoice({ id: "in_2" }));

    expect(sendMail).toHaveBeenCalledTimes(2);
  });

  it("gives the claim back when the send fails, so a redelivery can send it", async () => {
    const { fail, sendMail, sentBillingEmail } = setup();
    sendMail.mockRejectedValueOnce(new Error("SendGrid down"));

    await expect(fail()).rejects.toThrow("SendGrid down");
    expect(sentBillingEmail.release).toHaveBeenCalledWith(
      {},
      "renewal-failed:in_1",
    );
    await expect(fail()).resolves.toBe("sent");
  });

  it("sends nothing to a user without an email address", async () => {
    const { fail, sendMail, getById, sentBillingEmail } = setup();
    getById.mockResolvedValueOnce({ email: "" });

    await expect(fail()).resolves.toBe("no-recipient");
    expect(sendMail).not.toHaveBeenCalled();
    expect(sentBillingEmail.claim).not.toHaveBeenCalled();
  });
});

describe("emailPlanEnded", () => {
  it("says plainly that a plan ended because its renewal went unpaid", async () => {
    const { end, sendMail } = setup();

    await expect(end()).resolves.toBe("sent");

    const mail = mailOf(sendMail);
    expect(mail.subject).toBe("Your Premium · Yearly plan has ended");
    expect(mail.text).toContain("your account is on the Free plan");
    expect(mail.text).toContain("Nothing in your ledgers is deleted");
    expect(mail.html).toContain('href="https://beancount.io/settings/billing"');
  });

  it("says nothing of a plan canceled for any other reason", async () => {
    const { end, sendMail } = setup();

    for (const reason of [
      "cancellation_requested",
      "payment_disputed",
      null,
    ] as const) {
      await expect(end(canceled(reason))).resolves.toBe("not-applicable");
    }
    expect(sendMail).not.toHaveBeenCalled();
  });

  it("says nothing of a subscription that never started, or another product's", async () => {
    const { end, sendMail } = setup();

    await expect(
      end(canceled("payment_failed", { status: "incomplete_expired" })),
    ).resolves.toBe("not-applicable");
    await expect(
      end(canceled("payment_failed", {}, "price_other")),
    ).resolves.toBe("not-applicable");
    expect(sendMail).not.toHaveBeenCalled();
  });

  it("sends once per subscription, whatever Stripe redelivers", async () => {
    const { end, sendMail, sentBillingEmail } = setup();

    await end();
    await expect(end()).resolves.toBe("already-sent");

    expect(sendMail).toHaveBeenCalledTimes(1);
    expect(sentBillingEmail.claim).toHaveBeenCalledWith(
      {},
      "renewal-final:sub_1",
    );
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

  it("reminds nobody whose plan is set to end on or before the renewal", async () => {
    const { remind, sendMail } = setup();

    for (const cancel_at of [RENEWAL, RENEWAL - 86_400]) {
      await expect(
        remind(subscription(PREMIUM_YEARLY, { cancel_at })),
      ).resolves.toBe("not-applicable");
    }
    expect(sendMail).not.toHaveBeenCalled();
  });

  it("still reminds a subscriber whose plan ends after this renewal", async () => {
    const { remind } = setup();

    await expect(
      remind(subscription(PREMIUM_YEARLY, { cancel_at: RENEWAL + 86_400 })),
    ).resolves.toBe("sent");
  });

  it("reminds once per renewal, and again at next year's", async () => {
    const { remind, sendMail } = setup();

    await remind();
    await expect(remind()).resolves.toBe("already-sent");
    await remind(subscription(PREMIUM_YEARLY, {}, RENEWAL + 31_536_000));

    expect(sendMail).toHaveBeenCalledTimes(2);
  });
});
