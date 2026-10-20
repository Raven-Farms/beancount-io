import { createAuthMailJob } from "../auth-mail-job";
import { JobScheduler } from "../../job-scheduler";
import type { AppLayers } from "@/foundation/composition";
import type { AppConfig } from "@/config/config";
import cron from "node-cron";

jest.mock("node-cron", () => ({
  schedule: jest.fn(() => ({ stop: jest.fn() })),
}));

it("runs the durable auth mail worker every five seconds", async () => {
  const processBatch = jest.fn().mockResolvedValue(undefined);
  const job = createAuthMailJob(
    { services: { authMail: { processBatch } } } as unknown as AppLayers,
    {} as AppConfig,
  );
  expect(job.schedule).toBe("*/5 * * * * *");
  await job.task();
  expect(processBatch).toHaveBeenCalledTimes(1);
});

it("registers the worker in production and stops it with the other jobs", () => {
  const scheduler = new JobScheduler(
    {} as AppLayers,
    { env: "production" } as AppConfig,
  );
  scheduler.start();
  expect(cron.schedule).toHaveBeenCalledWith(
    "*/5 * * * * *",
    expect.any(Function),
  );
  scheduler.stop();
  const jobs = jest.mocked(cron.schedule).mock.results;
  expect(
    jobs.every((result) => result.value.stop.mock.calls.length === 1),
  ).toBe(true);
});
