import { requestPlatform } from "@/server/api/request-platform";
import { z } from "@/shared/zod-openapi-setup";
import { LedgerTemplate } from "@/features/ledger/workflow/ledger-workflow.types";
import { setupCatalog, type PresetId } from "@/features/ledger/setup";
import { v1Route } from "@/server/rest/v1-route";
import { json } from "@/server/rest/v1-schemas";
import { ledgerPathSchema, ledgerIdOf } from "./schemas";
const name = z
  .string()
  .max(100)
  .regex(/^[a-z0-9_-]+$/)
  .describe(
    "The ledger's name: lowercase letters, numbers, hyphens, and underscores, up to 100 characters.",
  );
const description = z
  .string()
  .nullish()
  .describe("A short description shown with the ledger.");
const ledgerSetupInput = z
  .object({
    preset: z
      .enum(
        setupCatalog.presets.map((preset) => preset.id) as [
          PresetId,
          ...PresetId[],
        ],
      )
      .describe("Setup preset id (ADR021)."),
    title: z.string().max(200).optional(),
    operatingCurrency: z.string().regex(/^[A-Z]{3}$/).optional(),
    historyStart: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
    capabilities: z
      .record(z.string(), z.enum(["enabled", "declined", "deferred"]))
      .optional(),
    accounts: z
      .array(
        z
          .object({
            name: z.string(),
            currency: z.string().regex(/^[A-Z]{3}$/).optional(),
            openingState: z.enum(["unknown", "zero", "known"]).optional(),
            amount: z.string().regex(/^-?\d+(\.\d+)?$/).optional(),
          })
          .strict(),
      )
      .optional(),
  })
  .strict();
export const ledgerCreateInput = z
  .object({
    name,
    description,
    private: z
      .boolean()
      .nullish()
      .describe(
        "true or omitted keeps the ledger visible only to its owner and collaborators; false makes it public, readable by anyone.",
      ),
    template: z
      .nativeEnum(LedgerTemplate)
      .nullish()
      .describe(
        "STARTER (the default) has options and accounts without transactions; SAMPLE has demonstration transactions.",
      ),
    setup: ledgerSetupInput.nullish(),
    requestId: z.string().min(1).max(200).nullish(),
  })
  .strict();
export const ledgerPreviewInput = z
  .object({ setup: ledgerSetupInput })
  .strict();
export const ledgerPreviewResultSchema = z.object({
  preset: z.string(),
  operatingCurrency: z.string(),
  historyStart: z.string(),
  accounts: z.array(z.string()),
  files: z.record(z.string(), z.string()),
});
export const ledgerUpdateInput = z
  .object({
    name: name.nullish(),
    description,
    private: z
      .boolean()
      .nullish()
      .describe(
        "true makes the ledger visible only to its owner and collaborators; false makes it public, readable by anyone; omitted leaves it as it is.",
      ),
  })
  .strict();
export const ledgerDeleteInput = z.object({}).strict();
export const ledgerResultSchema = z.object({
  id: z.string(),
  name: z.string(),
  fullName: z.string(),
  sshUrl: z.string(),
  httpUrl: z.string(),
  empty: z.boolean(),
  private: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
  size: z.number(),
  description: z.string().nullish(),
  permissions: z
    .object({ admin: z.boolean(), pull: z.boolean(), push: z.boolean() })
    .optional(),
  isStarred: z.boolean().optional(),
});
export const LEDGER_LIFECYCLE_ROUTES = [
  v1Route({
    method: "post",
    path: "/api-gateway/v1/ledgers",
    operationId: "createLedger",
    summary: "Create a ledger",
    description:
      "Create a ledger for the authenticated user under existing administrative account authority and tier limits. STARTER (the default, including null) contains options and accounts without transactions or opening balances; SAMPLE contains demonstration transactions. Existing ledgers are unchanged. This is an account operation even for a ledger-pinned credential.",
    body: ledgerCreateInput,
    responses: { 200: json("Created ledger", ledgerResultSchema) },
    handler: async ({ layers }, { identity, body, ctx }) =>
      layers.workflows.ledger.createLedger({
        identity,
        input: body,
        platform: requestPlatform(ctx.headers),
      }),
  }),
  v1Route({
    method: "post",
    path: "/api-gateway/v1/ledgers/preview",
    operationId: "previewLedgerSetup",
    summary: "Preview a ledger setup without creating it",
    description:
      "Return the files, account list, and validation result a setup specification (ADR021) would create, without creating anything. Uses the same LEDGER_CREATE authority as creation.",
    body: ledgerPreviewInput,
    responses: {
      200: json("Setup preview", ledgerPreviewResultSchema),
    },
    handler: async ({ layers }, { identity, body }) =>
      layers.workflows.ledger.previewLedgerSetup({
        identity,
        setup: body.setup,
      }),
  }),
  v1Route({
    method: "put",
    path: "/api-gateway/v1/ledgers/{owner}/{name}",
    operationId: "updateLedger",
    summary: "Update a ledger",
    description:
      "Update ledger name, description, or visibility. Requires current administrative authority over the addressed ledger and respects the credential pin.",
    params: ledgerPathSchema,
    body: ledgerUpdateInput,
    responses: { 200: json("Updated ledger", ledgerResultSchema) },
    handler: async ({ layers }, { identity, params, body }) =>
      layers.workflows.ledger.updateLedger({
        identity,
        ledgerId: ledgerIdOf(params),
        input: body,
      }),
  }),
  v1Route({
    method: "delete",
    path: "/api-gateway/v1/ledgers/{owner}/{name}",
    operationId: "deleteLedger",
    summary: "Delete a ledger",
    description:
      "Delete the repository and perform the existing linked-bank cleanup. Requires current administrative authority and respects the credential pin. Applies immediately; no preview.",
    params: ledgerPathSchema,
    responses: {
      200: json(
        "Deleted ledger identifier",
        z.object({ ledgerId: z.string() }),
      ),
    },
    handler: async ({ layers }, { identity, params }) =>
      layers.workflows.ledger.deleteLedger({
        identity,
        ledgerId: ledgerIdOf(params),
      }),
  }),
];
