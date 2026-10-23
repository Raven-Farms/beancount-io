import { drizzle } from "drizzle-orm/node-postgres";
import type { Logger } from "drizzle-orm/logger";
import { logger } from "@/shared/logger";
import { closeDatabaseConnection, createDatabaseConnection } from "./drizzle";

jest.mock("drizzle-orm/node-postgres", () => ({
  drizzle: jest.fn(() => ({})),
}));
jest.mock("pg", () => ({
  Pool: jest.fn(() => ({
    connect: jest.fn(async () => ({ query: jest.fn(), release: jest.fn() })),
    end: jest.fn(async () => undefined),
  })),
}));
jest.mock("@/shared/logger", () => {
  const logger = { debug: jest.fn(), child: jest.fn() };
  logger.child.mockReturnValue(logger);
  return { logger };
});

afterEach(async () => {
  await closeDatabaseConnection();
  jest.clearAllMocks();
});

it("logs SQL with placeholders without interpolating or serializing auth parameters", async () => {
  await createDatabaseConnection(
    "postgres://synthetic:synthetic@localhost/test",
  );
  const sqlLogger = (drizzle as unknown as jest.Mock).mock.calls[0][1]
    .logger as Logger;
  const query =
    'insert into "auth_tokens" ("email", "token", "payload") values ($1, $2, $3)';
  const secret = "synthetic-private-reset-token";
  const toJSON = jest.fn(() => ({ otp: secret }));

  sqlLogger.logQuery(query, [
    `${secret}@example.com`,
    secret,
    { otp: secret, toJSON },
  ]);

  expect(logger.debug).toHaveBeenCalledTimes(1);
  expect(logger.debug).toHaveBeenCalledWith(query);
  expect(toJSON).not.toHaveBeenCalled();
  expect(JSON.stringify((logger.debug as jest.Mock).mock.calls)).not.toContain(
    secret,
  );
});
