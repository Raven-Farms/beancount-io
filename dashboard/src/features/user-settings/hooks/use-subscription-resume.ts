import { useState } from "react";
import { useMutation } from "@apollo/client/react";
import {
  ResumeSubscriptionDocument,
  type ResumeSubscriptionMutation,
  GetSubscriptionStatusDocument,
} from "@/graphql/definitions";
import { toast } from "sonner";
import { useTranslations } from "@/common/hooks/use-translations";
import { useErrorMessage } from "@/common/lib/errors/error-message";

export const useSubscriptionResume = () => {
  const { t } = useTranslations();
  const formatError = useErrorMessage();
  const [showResumeDialog, setShowResumeDialog] = useState(false);
  const [selectedResumeSubscription, setSelectedResumeSubscription] = useState<{
    id: string;
    clientId: string;
    renewalDate: string;
  } | null>(null);

  // Status refetches as part of the mutation, so `loading` covers it.
  const [resumeSubscription, { loading }] =
    useMutation<ResumeSubscriptionMutation>(ResumeSubscriptionDocument, {
      refetchQueries: [{ query: GetSubscriptionStatusDocument }],
      awaitRefetchQueries: true,
    });

  const handleResumeClick = (
    subscriptionId: string,
    clientId: string,
    renewalDate: string,
  ) => {
    setSelectedResumeSubscription({
      id: subscriptionId,
      clientId,
      renewalDate,
    });
    setShowResumeDialog(true);
  };

  /** Returns whether the pending cancellation was withdrawn. */
  const handleResumeConfirm = async (): Promise<boolean> => {
    if (!selectedResumeSubscription) return false;
    try {
      const response = await resumeSubscription({
        variables: {
          subscriptionId: selectedResumeSubscription.id,
          clientId: selectedResumeSubscription.clientId,
        },
      });
      const result = response.data?.resumeSubscription;
      if (result?.success) {
        toast.success(t("userSettings.subscriptionResumedSuccess"));
        return true;
      }
      toast.error(
        result?.message || t("userSettings.failedToResumeSubscription"),
      );
      return false;
    } catch (error) {
      toast.error(formatError(error));
      return false;
    } finally {
      setShowResumeDialog(false);
      setSelectedResumeSubscription(null);
    }
  };

  return {
    loading,
    showResumeDialog,
    setShowResumeDialog,
    selectedResumeSubscription,
    handleResumeClick,
    handleResumeConfirm,
  };
};
