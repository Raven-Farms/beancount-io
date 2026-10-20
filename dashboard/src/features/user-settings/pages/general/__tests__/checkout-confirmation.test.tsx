import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, renderHook, screen } from "@testing-library/react";
import * as locales from "@/i18n/locales";
import { CheckoutConfirmation } from "../checkout-confirmation";
import {
  CONFIRMATION_TIMEOUT_MS,
  useCheckoutConfirmation,
} from "../use-checkout-confirmation";

const t = (key: string, params?: Record<string, string | number>) =>
  params ? `${key}:${JSON.stringify(params)}` : key;

describe("useCheckoutConfirmation", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("polls until the webhook records the subscription, then stops", () => {
    const refetch = vi.fn();
    const { result, rerender } = renderHook(
      ({ recorded }) => useCheckoutConfirmation(true, recorded, refetch),
      { initialProps: { recorded: false } },
    );
    expect(result.current).toBe("confirming");

    act(() => vi.advanceTimersByTime(4_000));
    expect(refetch).toHaveBeenCalledTimes(2);

    rerender({ recorded: true });
    expect(result.current).toBe("done");
    act(() => vi.advanceTimersByTime(10_000));
    expect(refetch).toHaveBeenCalledTimes(2);
  });

  it("says the payment is received, not failed, once the wait runs out", () => {
    const { result } = renderHook(() =>
      useCheckoutConfirmation(true, false, vi.fn()),
    );
    act(() => vi.advanceTimersByTime(CONFIRMATION_TIMEOUT_MS));
    expect(result.current).toBe("pending");
  });

  it("does nothing without a Checkout return", () => {
    const refetch = vi.fn();
    renderHook(() => useCheckoutConfirmation(false, false, refetch));
    act(() => vi.advanceTimersByTime(CONFIRMATION_TIMEOUT_MS));
    expect(refetch).not.toHaveBeenCalled();
  });
});

describe("CheckoutConfirmation", () => {
  const base = {
    planLabel: "Premium · Yearly",
    planName: "Premium",
    renewal: { date: "Oct 17, 2027", amount: "$143.88" },
    unlocked: "5 ledgers",
    t,
    onRefresh: vi.fn(),
    onDismiss: vi.fn(),
  };

  it("shows the plan, the renewal, what was unlocked and the way back", () => {
    render(
      <CheckoutConfirmation
        {...base}
        state="done"
        returnTo="/ledger/alice/books"
      />,
    );
    expect(
      screen.getByText(/userSettings.checkoutDone.*Premium · Yearly/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Oct 17, 2027/)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "userSettings.backToWork" }),
    ).toHaveAttribute("href", "/ledger/alice/books");
    // The way back replaces, not joins, the default next step.
    expect(
      screen.queryByRole("link", { name: /userSettings.startUsingPlan/ }),
    ).not.toBeInTheDocument();
  });

  it("leads into the product when there is nowhere to return to", () => {
    render(<CheckoutConfirmation {...base} state="done" returnTo={null} />);
    expect(
      screen.queryByRole("link", { name: "userSettings.backToWork" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: 'userSettings.startUsingPlan:{"plan":"Premium"}',
      }),
    ).toHaveAttribute("href", "/ledger");
    expect(
      screen.getByRole("button", { name: "userSettings.viewBilling" }),
    ).toBeInTheDocument();
  });

  it("renders a slow webhook as information with a refresh, never as an error", () => {
    render(<CheckoutConfirmation {...base} state="pending" returnTo={null} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "userSettings.checkoutPending",
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    screen.getByRole("button", { name: "userSettings.refresh" }).click();
    expect(base.onRefresh).toHaveBeenCalled();
  });
});

describe("CheckoutConfirmation in other languages", () => {
  const ALL = locales as unknown as Record<string, Record<string, string>>;
  /** The app's translator for one language, placeholders filled in. */
  const translator =
    (lang: string) => (key: string, params?: Record<string, string | number>) =>
      Object.entries(params ?? {}).reduce(
        (message, [name, value]) => message.replace(`{${name}}`, String(value)),
        ALL[lang][key] ?? key,
      );

  it.each(["zh", "fa"])(
    "leads into the product in %s with the plan named in that language",
    (lang) => {
      const t = translator(lang);
      const plan = t("aiAgent.premiumTier");
      render(
        <CheckoutConfirmation
          state="done"
          planLabel={plan}
          planName={plan}
          renewal={null}
          unlocked={null}
          returnTo={null}
          t={t}
          onRefresh={vi.fn()}
          onDismiss={vi.fn()}
        />,
      );

      const link = screen.getByRole("link", {
        name: t("userSettings.startUsingPlan", { plan }),
      });
      expect(link).toHaveAttribute("href", "/ledger");
      expect(link.textContent).toContain(plan);
      expect(link.textContent).not.toBe(
        translator("en")("userSettings.startUsingPlan", { plan }),
      );
      expect(t("userSettings.checkoutCanceled")).not.toBe(
        translator("en")("userSettings.checkoutCanceled"),
      );
    },
  );
});
