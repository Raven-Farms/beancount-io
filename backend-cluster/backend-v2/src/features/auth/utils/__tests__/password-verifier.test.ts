import bcrypt from "bcryptjs";
import { ServiceUnavailableError } from "@/shared/errors";
import { verifyPasswordWithCapacity } from "../password-verifier";

afterEach(() => jest.restoreAllMocks());

it("performs a real cost-10 comparison for absent credentials and always refuses", async () => {
  const compare = jest.spyOn(bcrypt, "compare");

  await expect(
    verifyPasswordWithCapacity("dummy-password-comparison-only"),
  ).resolves.toBe(false);

  expect(compare).toHaveBeenCalledTimes(1);
  expect(bcrypt.getRounds(compare.mock.calls[0][1] as string)).toBe(10);
});

it("caps real and dummy comparisons together at eight without queueing overflow", async () => {
  let release!: (value: boolean) => void;
  const pending = new Promise<boolean>((resolve) => {
    release = resolve;
  });
  const compare = jest
    .spyOn(bcrypt, "compare")
    .mockImplementation(() => pending as never);
  const verify = jest.fn(() => pending);
  const attempts = Array.from({ length: 8 }, (_, i) =>
    verifyPasswordWithCapacity("password", i % 2 ? verify : undefined),
  );

  try {
    await expect(
      verifyPasswordWithCapacity("password", verify),
    ).rejects.toBeInstanceOf(ServiceUnavailableError);
    await expect(verifyPasswordWithCapacity("password")).rejects.toBeInstanceOf(
      ServiceUnavailableError,
    );
    expect(compare).toHaveBeenCalledTimes(4);
    expect(verify).toHaveBeenCalledTimes(4);
  } finally {
    release(true);
    await Promise.all(attempts);
  }

  await expect(
    verifyPasswordWithCapacity("password", async () => true),
  ).resolves.toBe(true);
  expect(verify).toHaveBeenCalledTimes(4);
});

it("releases capacity when known-account verification throws", async () => {
  const failure = new Error("verification failed");
  for (let i = 0; i < 12; i += 1) {
    await expect(
      verifyPasswordWithCapacity("password", async () => {
        throw failure;
      }),
    ).rejects.toBe(failure);
  }
  await expect(
    verifyPasswordWithCapacity("password", async () => true),
  ).resolves.toBe(true);
});

it("releases capacity when dummy comparison rejects", async () => {
  const failure = new Error("comparison failed");
  jest
    .spyOn(bcrypt, "compare")
    .mockImplementation(() => Promise.reject(failure));
  for (let i = 0; i < 12; i += 1) {
    await expect(verifyPasswordWithCapacity("password")).rejects.toBe(failure);
  }
  await expect(
    verifyPasswordWithCapacity("password", async () => true),
  ).resolves.toBe(true);
});
