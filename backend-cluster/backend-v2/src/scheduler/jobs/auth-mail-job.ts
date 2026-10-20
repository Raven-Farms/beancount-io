import type { JobFactory } from "../types";

export const createAuthMailJob: JobFactory = (layers) => ({
  schedule: "*/5 * * * * *",
  task: () => layers.services.authMail.processBatch(),
});
