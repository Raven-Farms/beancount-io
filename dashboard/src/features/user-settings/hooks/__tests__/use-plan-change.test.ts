import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import {
  GetCurrentUserDocument,
  GetSubscriptionStatusDocument,
} from "@/graphql/definitions";
import { useChangePlan } from "../use-plan-change";

const { mockUseMutation } = vi.hoisted(() => ({
  mockUseMutation: vi.fn(() => [vi.fn(), { loading: false }]),
}));
vi.mock("@apollo/client/react", () => ({
  useMutation: mockUseMutation,
  useLazyQuery: () => [vi.fn(), { loading: false }],
}));

describe("useChangePlan", () => {
  it("refetches the plan and the subscription before the change resolves, so callers need no refetch of their own", () => {
    renderHook(() => useChangePlan());

    const [, options] = mockUseMutation.mock.calls[0] as unknown as [
      unknown,
      { refetchQueries: { query: unknown }[]; awaitRefetchQueries: boolean },
    ];
    expect(options.refetchQueries).toEqual([
      { query: GetCurrentUserDocument },
      { query: GetSubscriptionStatusDocument },
    ]);
    expect(options.awaitRefetchQueries).toBe(true);
  });
});
