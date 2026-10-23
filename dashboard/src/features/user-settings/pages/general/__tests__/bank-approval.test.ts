import { beforeEach, describe, expect, it, vi } from "vitest";
import { approveBankPayment } from "../bank-approval";
import { stripePlanConfig } from "../stripe-config";

const { mockLoadStripe, stripe } = vi.hoisted(() => ({
  mockLoadStripe: vi.fn(),
  stripe: {
    retrievePaymentIntent: vi.fn(),
    handleNextAction: vi.fn(),
    confirmPayment: vi.fn(),
  },
}));
vi.mock("@stripe/stripe-js", () => ({ loadStripe: mockLoadStripe }));

const RETURN_URL = "https://beancount.io/settings/billing";
const intent = (status: string) => ({ paymentIntent: { status } });

beforeEach(() => {
  vi.clearAllMocks();
  mockLoadStripe.mockResolvedValue(stripe);
});

describe("approveBankPayment", () => {
  it("loads Stripe.js with the live publishable key", async () => {
    stripe.retrievePaymentIntent.mockResolvedValue(intent("succeeded"));

    await approveBankPayment("pi_secret", RETURN_URL);

    expect(mockLoadStripe).toHaveBeenCalledWith(
      stripePlanConfig.publishableKey,
    );
    expect(stripePlanConfig.publishableKey).toMatch(/^pk_live_/);
  });

  it("shows the bank's challenge, and reports the payment approved", async () => {
    stripe.retrievePaymentIntent.mockResolvedValue(intent("requires_action"));
    stripe.handleNextAction.mockResolvedValue(intent("succeeded"));

    await expect(approveBankPayment("pi_secret", RETURN_URL)).resolves.toBe(
      "approved",
    );
    expect(stripe.handleNextAction).toHaveBeenCalledWith({
      clientSecret: "pi_secret",
    });
  });

  it("confirms an unconfirmed payment with its own card, redirecting only if the bank must", async () => {
    stripe.retrievePaymentIntent.mockResolvedValue(
      intent("requires_confirmation"),
    );
    stripe.confirmPayment.mockResolvedValue(intent("succeeded"));

    await expect(approveBankPayment("pi_secret", RETURN_URL)).resolves.toBe(
      "approved",
    );
    expect(stripe.confirmPayment).toHaveBeenCalledWith({
      clientSecret: "pi_secret",
      confirmParams: { return_url: RETURN_URL },
      redirect: "if_required",
    });
  });

  it.each([
    ["a card error", { type: "card_error", code: "card_declined" }],
    [
      "a failed challenge",
      {
        type: "invalid_request_error",
        code: "payment_intent_authentication_failure",
        payment_intent: { status: "requires_payment_method" },
      },
    ],
  ])("reports %s as declined", async (_label, error) => {
    stripe.retrievePaymentIntent.mockResolvedValue(intent("requires_action"));
    stripe.handleNextAction.mockResolvedValue({ error });

    await expect(approveBankPayment("pi_secret", RETURN_URL)).resolves.toBe(
      "declined",
    );
  });

  it("reports a payment still in flight as pending", async () => {
    stripe.retrievePaymentIntent.mockResolvedValue(intent("requires_action"));
    stripe.handleNextAction.mockResolvedValue(intent("processing"));

    await expect(approveBankPayment("pi_secret", RETURN_URL)).resolves.toBe(
      "pending",
    );
  });

  it.each([
    ["Stripe.js does not load", () => mockLoadStripe.mockResolvedValue(null)],
    [
      "the script fails to fetch",
      () => mockLoadStripe.mockRejectedValue(new Error("blocked")),
    ],
    [
      "the payment cannot be read",
      () =>
        stripe.retrievePaymentIntent.mockResolvedValue({
          error: { type: "invalid_request_error" },
        }),
    ],
    [
      "Stripe cannot be reached mid-challenge",
      () => {
        stripe.retrievePaymentIntent.mockResolvedValue(
          intent("requires_action"),
        );
        stripe.handleNextAction.mockResolvedValue({
          error: { type: "api_connection_error" },
        });
      },
    ],
  ])("hands over to Stripe's page when %s", async (_label, arrange) => {
    arrange();

    await expect(approveBankPayment("pi_secret", RETURN_URL)).resolves.toBe(
      "unavailable",
    );
  });
});
