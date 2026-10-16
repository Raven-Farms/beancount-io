import type { LLMClient } from "../llm-client";
import { callLLM } from "../call-llm";
import type { ExtractTransactionsResult } from "../../types";
import { prepareLlmMessage } from "../prepare-llm-message";
import { groundTransactionDescriptions } from "./ground-descriptions";
import {
  buildTransactionSystemPrompt,
  buildTransactionTextAnalysisPrompt,
  buildTransactionImageAnalysisPrompt,
  buildTransactionFileAnalysisPrompt,
} from "./prompts";

export async function extractTransactionsFromFile({
  llmClient,
  fileUrl,
  format,
  mediaType,
}: {
  llmClient: LLMClient;
  fileUrl: string;
  format: string;
  mediaType?: string;
}): Promise<ExtractTransactionsResult & { removedDescriptionCount?: number }> {
  const { system, messages, sourceText } = await prepareLlmMessage({
    fileUrl,
    format,
    mediaType,
    prompts: {
      system: buildTransactionSystemPrompt,
      text: buildTransactionTextAnalysisPrompt,
      image: buildTransactionImageAnalysisPrompt,
      file: buildTransactionFileAnalysisPrompt,
    },
  });
  const result = await callLLM({ llmClient, system, messages });
  if (sourceText === undefined) return result;
  return {
    ...result,
    ...groundTransactionDescriptions(
      result.transactions,
      sourceText,
      format,
      mediaType,
    ),
  };
}
