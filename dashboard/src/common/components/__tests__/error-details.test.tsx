import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { toast } from "sonner";
import zhCommon from "@/i18n/locales/common/zh";
import { ErrorDetails } from "../error-details";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));
vi.mock("@/common/hooks/use-translations", async () => {
  const { default: translations } = await import("@/i18n/locales/common/zh");
  return {
    useTranslations: () => ({
      t: (key: keyof typeof translations) => translations[key]?.message ?? key,
    }),
  };
});

const originalUrl = window.location.href;
const challenge = `rcv_${"a".repeat(64)}`;
const email = "private.person@example.com";
const code = "006731";
const password = "synthetic password/only";
const accessToken = "synthetic/access+token";
const fragmentToken = "private-fragment-token";
const time = new Date("2026-10-20T09:10:11.000Z");
const privateValues = [
  challenge,
  email,
  code,
  password,
  accessToken,
  fragmentToken,
  encodeURIComponent(email),
  encodeURIComponent(password),
  encodeURIComponent(accessToken),
];
const writeText = vi.fn<(value: string) => Promise<void>>();

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(time);
  writeText.mockResolvedValue(undefined);
  const search = new URLSearchParams({
    recovery: challenge,
    email,
    code,
    password,
    access_token: accessToken,
  });
  window.history.replaceState(
    null,
    "",
    `/auth/login/?${search}#token=${fragmentToken}`,
  );
  vi.stubGlobal("navigator", {
    userAgent: `FixtureBrowser/123 proof=${challenge}`,
    clipboard: { writeText },
  });
});
afterEach(() => {
  cleanup();
  window.history.replaceState(null, "", originalUrl);
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function failure() {
  const error = new TypeError(
    `Recovery screen failed; proof=${challenge}; email=${email}; code=${code}; password=${password}; access=${accessToken}; fragment=${fragmentToken}`,
  );
  error.stack = Array.from(
    { length: 30 },
    (_, index) => `    at frame${index} (${window.location.href})`,
  ).join("\n");
  return {
    error,
    componentStack: Array.from(
      { length: 30 },
      (_, index) =>
        `    at RecoveryForm${index} email=${encodeURIComponent(email)} password=${encodeURIComponent(password)} access=${encodeURIComponent(accessToken)}`,
    ).join("\n"),
  };
}

function expectPrivateValuesAbsent(value: string) {
  for (const secret of privateValues) expect(value).not.toContain(secret);
}

describe("ErrorDetails recovery-page diagnostics", () => {
  it("renders and copies a sanitized report while preserving useful diagnostics and truncation", async () => {
    const { container } = render(<ErrorDetails {...failure()} />);
    const summary = screen.getByText(zhCommon["common.errorDetails"].message);
    const details = summary.closest("details")!;
    expect(details).not.toHaveAttribute("open");
    fireEvent.click(summary);
    expect(details).toHaveAttribute("open");
    const report = container.querySelector("pre")!.textContent!;

    expectPrivateValuesAbsent(report);
    expect(report).toContain("TypeError: Recovery screen failed");
    expect(report).toContain(`URL: ${window.location.origin}/auth/login/\n`);
    expect(report).toContain("Time: 2026-10-20T09:10:11.000Z");
    expect(report).toContain("Browser: FixtureBrowser/123");
    expect(report).toContain("at frame19");
    expect(report).not.toContain("at frame20");
    expect(report).toContain("at RecoveryForm19");
    expect(report).not.toContain("at RecoveryForm20");
    expect(report).toContain("…");

    fireEvent.click(
      screen.getByRole("button", { name: zhCommon["common.copy"].message }),
    );

    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    const copied = writeText.mock.calls[0][0];
    expect(copied).toBe(report);
    expectPrivateValuesAbsent(copied);
    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith(
        zhCommon["common.copiedToClipboard"].message,
      ),
    );
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("keeps clipboard failure feedback localized without exposing its sensitive exception", async () => {
    writeText.mockRejectedValue(
      new Error(`Clipboard refused proof ${challenge}`),
    );
    render(<ErrorDetails {...failure()} />);
    fireEvent.click(screen.getByText(zhCommon["common.errorDetails"].message));
    fireEvent.click(
      screen.getByRole("button", { name: zhCommon["common.copy"].message }),
    );

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        zhCommon["common.copyFailed"].message,
      ),
    );
    expect(toast.error).toHaveBeenCalledTimes(1);
    expect(toast.success).not.toHaveBeenCalled();
    expectPrivateValuesAbsent(writeText.mock.calls[0][0]);
    expect(
      screen.queryByText(/Clipboard refused proof/),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: zhCommon["common.copy"].message }),
    ).toBeEnabled();
  });
});
