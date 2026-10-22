import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { Combobox } from "../combobox";
import { Popover, PopoverContent, PopoverTrigger } from "../popover";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "../dialog";

vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ t: (key: string) => key }),
}));

/** An IME's Escape cancels its composition, not the dialog (w4/292). */
function Harness({
  onOpenChange,
  onEscapeKeyDown,
  withPicker = false,
}: {
  onOpenChange: (open: boolean) => void;
  onEscapeKeyDown?: (event: KeyboardEvent) => void;
  withPicker?: boolean;
}) {
  const [open, setOpen] = useState(true);
  const [draft, setDraft] = useState("");
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
        setOpen(next);
      }}
    >
      <DialogContent onEscapeKeyDown={onEscapeKeyDown}>
        <DialogTitle>Open Account</DialogTitle>
        <DialogDescription>QA</DialogDescription>
        <input
          aria-label="Account Name"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        {withPicker && (
          <Combobox
            options={[{ value: "USD", label: "USD" }]}
            value=""
            onValueChange={() => {}}
            allowCustom
            triggerOn="blur"
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

const field = () => screen.getByLabelText("Account Name");

describe("Dialog Escape during IME composition", () => {
  it.each([
    { isComposing: true, keyCode: 27 },
    { isComposing: false, keyCode: 229 },
  ])(
    "keeps the dialog and its draft for a composing Escape (%o), then closes on an ordinary one",
    (composing) => {
      const onOpenChange = vi.fn();
      render(<Harness onOpenChange={onOpenChange} />);
      field().focus();
      fireEvent.compositionStart(field());
      fireEvent.change(field(), {
        target: { value: "Assets:Qa-20261020:東京" },
      });

      fireEvent.keyDown(field(), { key: "Escape", ...composing });
      expect(onOpenChange).not.toHaveBeenCalled();
      expect(field()).toHaveValue("Assets:Qa-20261020:東京");

      fireEvent.compositionEnd(field());
      fireEvent.keyDown(field(), { key: "Escape", keyCode: 27 });
      expect(onOpenChange).toHaveBeenCalledExactlyOnceWith(false);
      expect(screen.queryByRole("dialog")).toBeNull();
    },
  );

  it("leaves an ordinary Escape to the caller's handler, which may keep it open", () => {
    const onOpenChange = vi.fn();
    const onEscapeKeyDown = vi.fn((event: KeyboardEvent) =>
      event.preventDefault(),
    );
    render(
      <Harness onOpenChange={onOpenChange} onEscapeKeyDown={onEscapeKeyDown} />,
    );

    fireEvent.keyDown(field(), { key: "Escape", isComposing: true });
    expect(onEscapeKeyDown).not.toHaveBeenCalled();

    fireEvent.keyDown(field(), { key: "Escape", keyCode: 27 });
    expect(onEscapeKeyDown).toHaveBeenCalledTimes(1);
    expect(onOpenChange).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("keeps both a nested picker and the dialog open while composing", () => {
    const onOpenChange = vi.fn();
    render(<Harness onOpenChange={onOpenChange} withPicker />);
    const picker = screen.getByRole("combobox");
    picker.focus();
    fireEvent.keyDown(picker, { key: "ArrowDown", keyCode: 40 });
    expect(picker).toHaveAttribute("aria-expanded", "true");

    fireEvent.keyDown(picker, { key: "Escape", isComposing: true });
    expect(picker).toHaveAttribute("aria-expanded", "true");
    expect(onOpenChange).not.toHaveBeenCalled();

    fireEvent.keyDown(picker, { key: "Escape", keyCode: 27 });
    expect(picker).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("keeps a plain popover and its dialog open while composing (w4/318)", () => {
    const onOpenChange = vi.fn();
    render(
      <Dialog open onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogTitle>Switch</DialogTitle>
          <DialogDescription>QA</DialogDescription>
          <Popover defaultOpen>
            <PopoverTrigger>Pick</PopoverTrigger>
            <PopoverContent>
              <input aria-label="Search" defaultValue="東" />
            </PopoverContent>
          </Popover>
        </DialogContent>
      </Dialog>,
    );
    const search = screen.getByLabelText("Search");

    fireEvent.keyDown(search, { key: "Escape", isComposing: true });
    expect(screen.getByLabelText("Search")).toHaveValue("東");
    expect(onOpenChange).not.toHaveBeenCalled();

    // An ordinary Escape closes only the top layer, the popover.
    fireEvent.keyDown(search, { key: "Escape", keyCode: 27 });
    expect(screen.queryByLabelText("Search")).toBeNull();
    expect(onOpenChange).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});
