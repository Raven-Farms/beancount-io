import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, renderHook, screen } from "@testing-library/react";
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
  });

  it("offers only Billing when there is nowhere to return to", () => {
    render(<CheckoutConfirmation {...base} state="done" returnTo={null} />);
    expect(
      screen.queryByRole("link", { name: "userSettings.backToWork" }),
    ).not.toBeInTheDocument();
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
