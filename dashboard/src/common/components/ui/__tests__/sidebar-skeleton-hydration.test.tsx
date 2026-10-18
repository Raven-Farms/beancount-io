import { act } from "react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SidebarMenuSkeleton } from "../sidebar";

const skeletons = () => (
  <ul>
    {[0, 1, 2].map((index) => (
      <SidebarMenuSkeleton key={index} index={index} />
    ))}
  </ul>
);

afterEach(() => {
  vi.restoreAllMocks();
});

describe("SidebarMenuSkeleton widths (w3/567)", () => {
  it("renders the same widths on every render, server or browser", () => {
    expect(renderToString(skeletons())).toBe(renderToString(skeletons()));
    const widths = [
      ...renderToString(skeletons()).matchAll(/--skeleton-width:([\d.]+%)/g),
    ].map(([, width]) => width);
    expect(widths).toHaveLength(3);
    // Still varied from row to row.
    expect(new Set(widths).size).toBe(3);
  });

  it("hydrates server HTML without a mismatch", async () => {
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    const container = document.createElement("div");
    container.innerHTML = renderToString(skeletons());
    document.body.append(container);
    const recoverable = vi.fn();

    await act(async () => {
      hydrateRoot(container, skeletons(), {
        onRecoverableError: recoverable,
      });
    });

    const reported = consoleError.mock.calls.flat().join(" ");
    expect(reported).not.toMatch(/hydrat|did not match|didn't match/i);
    expect(recoverable).not.toHaveBeenCalled();
    container.remove();
  });
});
