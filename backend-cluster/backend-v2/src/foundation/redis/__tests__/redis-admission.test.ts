import { logger } from "@/shared/logger";
import { getRedisClient } from "../redis-utils";
import {
  clearFailureBudget,
  completeFailureBudget,
  consumeSlidingWindows,
  reserveFailureBudget,
} from "../redis-admission";

jest.mock("../redis-utils", () => ({ getRedisClient: jest.fn() }));
jest.mock("@/shared/logger", () => {
  const error = jest.fn();
  return { logger: { child: () => ({ error }) } };
});

const clientMock = jest.mocked(getRedisClient);
const errorLog = jest.mocked(
  logger.child({ module: "redis-admission-test" }).error,
);

beforeEach(() => {
  jest.clearAllMocks();
});

async function checkUnavailable(): Promise<void> {
  await expect(
    consumeSlidingWindows([{ key: "account", max: 10, windowMs: 1000 }]),
  ).resolves.toBeUndefined();
  await expect(
    reserveFailureBudget("account", 10, 1000),
  ).resolves.toBeUndefined();
  await expect(
    completeFailureBudget("account", 1000, "reservation", "success"),
  ).resolves.toBeUndefined();
  await expect(clearFailureBudget("account")).resolves.toBeUndefined();
}

it("reports unavailable rather than admitting an attempt before Redis initialization", async () => {
  clientMock.mockReturnValue(null);
  await checkUnavailable();
});

it("reports unavailable on Redis failure without logging command arguments or credentials", async () => {
  clientMock.mockReturnValue({
    eval: jest
      .fn()
      .mockRejectedValue(
        new Error("credential@example.com: secret command key"),
      ),
  } as unknown as NonNullable<ReturnType<typeof getRedisClient>>);

  await checkUnavailable();

  expect(errorLog.mock.calls).toEqual([
    ["Redis admission unavailable"],
    ["Redis admission unavailable"],
    ["Redis admission unavailable"],
    ["Redis admission unavailable"],
  ]);
});

it("refuses malformed admission results rather than silently admitting", async () => {
  const evalMock = jest.fn().mockResolvedValue([1, -1]);
  clientMock.mockReturnValue({ eval: evalMock } as unknown as NonNullable<
    ReturnType<typeof getRedisClient>
  >);

  await expect(
    consumeSlidingWindows([{ key: "account", max: 10, windowMs: 1000 }]),
  ).resolves.toBeUndefined();
  evalMock.mockResolvedValue("OK");
  await expect(
    reserveFailureBudget("account", 10, 1000),
  ).resolves.toBeUndefined();
});

it("rejects invalid or duplicate policies before mutating Redis", async () => {
  const evalMock = jest.fn();
  clientMock.mockReturnValue({ eval: evalMock } as unknown as NonNullable<
    ReturnType<typeof getRedisClient>
  >);

  await expect(
    consumeSlidingWindows([{ key: "account", max: 0, windowMs: 1000 }]),
  ).rejects.toThrow(RangeError);
  await expect(
    consumeSlidingWindows([
      { key: "account", max: 1, windowMs: 1000 },
      { key: "account", max: 2, windowMs: 2000 },
    ]),
  ).rejects.toThrow(RangeError);
  await expect(reserveFailureBudget("account", 1, -1)).rejects.toThrow(
    RangeError,
  );
  expect(evalMock).not.toHaveBeenCalled();
});
