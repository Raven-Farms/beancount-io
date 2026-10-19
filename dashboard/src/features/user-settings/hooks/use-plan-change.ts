import { useLazyQuery, useMutation } from "@apollo/client/react";
import {
  CancelScheduledPlanChangeDocument,
  type CancelScheduledPlanChangeMutation,
  type CancelScheduledPlanChangeMutationVariables,
  ChangePlanDocument,
  GetCurrentUserDocument,
  GetSubscriptionStatusDocument,
  PreviewPlanChangeDocument,
  type ChangePlanMutation,
  type ChangePlanMutationVariables,
  type GetCurrentUserQuery,
  type PreviewPlanChangeQuery,
  type PreviewPlanChangeQueryVariables,
} from "@/graphql/definitions";

/**
 * Ask the server what a plan change would do. Always a fresh read: the
 * amount is priced by Stripe at this moment, and its proration time is what
 * `useChangePlan` must confirm with.
 */
export const usePreviewPlanChange = () =>
  useLazyQuery<PreviewPlanChangeQuery, PreviewPlanChangeQueryVariables>(
    PreviewPlanChangeDocument,
    { fetchPolicy: "network-only" },
  );

/**
 * Apply an immediate change. On success the new tier is written into the
 * cached profile at once, and plan and status are refetched, so limits and
 * the Billing tab reflect it without a reload.
 */
export const useChangePlan = () =>
  useMutation<ChangePlanMutation, ChangePlanMutationVariables>(
    ChangePlanDocument,
    {
      refetchQueries: [
        { query: GetCurrentUserDocument },
        { query: GetSubscriptionStatusDocument },
      ],
      awaitRefetchQueries: true,
      update(cache, { data }) {
        const result = data?.changePlan;
        if (result?.status !== "ACTIVE" || !result.newTier) return;
        const existing = cache.readQuery<GetCurrentUserQuery>({
          query: GetCurrentUserDocument,
        });
        if (!existing?.userProfile) return;
        cache.writeQuery<GetCurrentUserQuery>({
          query: GetCurrentUserDocument,
          data: {
            userProfile: { ...existing.userProfile, tier: result.newTier },
          },
        });
      },
    },
  );

/**
 * Undo a scheduled plan change: the current plan continues. Status is
 * refetched so the Scheduled panel and the plan row reflect it.
 */
export const useCancelScheduledPlanChange = () =>
  useMutation<
    CancelScheduledPlanChangeMutation,
    CancelScheduledPlanChangeMutationVariables
  >(CancelScheduledPlanChangeDocument, {
    refetchQueries: [{ query: GetSubscriptionStatusDocument }],
    awaitRefetchQueries: true,
  });
