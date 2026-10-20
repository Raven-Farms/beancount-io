import { LedgerCollaboratorsWorkflow } from "../ledger-collaborators-workflow";
import { getUserTier } from "@/features/stripe/operations/get-user-tier";
import { SubscriptionTier } from "@/features/stripe/service/stripe";

jest.mock("@/features/stripe/operations/get-user-tier");
const mockGetUserTier = getUserTier as jest.Mock;

const identity = {
  userId: "usr_owner",
  method: "session",
  scopes: new Set<string>(),
} as const;

describe("LedgerCollaboratorsWorkflow collaborator limit", () => {
  const listLedgerCollaborators = jest.fn();
  const addOrUpdateLedgerCollaborator = jest.fn();
  let workflow: LedgerCollaboratorsWorkflow;

  beforeEach(() => {
    jest.clearAllMocks();
    // The owner plus one collaborator already on the ledger.
    listLedgerCollaborators.mockResolvedValue({
      data: {
        success: true,
        data: [{ login: "owner" }, { login: "existing" }],
      },
    });
    addOrUpdateLedgerCollaborator.mockResolvedValue({
      data: { success: true },
    });
    const favaApiClient = {
      collaborators: { listLedgerCollaborators, addOrUpdateLedgerCollaborator },
    };
    workflow = new LedgerCollaboratorsWorkflow(
      { getPublicApiClient: jest.fn(async () => favaApiClient) } as never,
      {} as never,
      { authorizeOrThrow: jest.fn(async () => ({ allowed: true })) } as never,
    );
  });

  const add = () =>
    workflow.addOrUpdateCollaborator({
      identity,
      ledgerId: "owner/main",
      collaborator: "newcomer",
      permission: "read",
    });

  it("refuses a new collaborator over a finite limit", async () => {
    mockGetUserTier.mockResolvedValue(SubscriptionTier.FREE);
    await expect(add()).rejects.toThrow(/Maximum number of collaborators/);
    expect(addOrUpdateLedgerCollaborator).not.toHaveBeenCalled();
  });

  it("treats -1 as unlimited", async () => {
    mockGetUserTier.mockResolvedValue(SubscriptionTier.ENTERPRISE);
    await expect(add()).resolves.toEqual(
      expect.objectContaining({ success: true }),
    );
    expect(addOrUpdateLedgerCollaborator).toHaveBeenCalledTimes(1);
  });
});
