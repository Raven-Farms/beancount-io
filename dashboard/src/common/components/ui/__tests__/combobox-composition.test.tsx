import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Combobox } from "../combobox";
import { SearchControlCombobox } from "../../ledger-search-controls";

vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ t: (key: string) => key }),
}));

/** An IME's composing Enter confirms text; it is not a commit (w4/286). */
const options = ["2016-08", "2016-09"].map((value) => ({
  value,
  label: value,
}));

function compose(input: HTMLElement, text: string) {
  fireEvent.compositionStart(input);
  fireEvent.change(input, { target: { value: text } });
}
const composingEnter = (input: HTMLElement, keyCode = 13) =>
  fireEvent.keyDown(input, { key: "Enter", keyCode, isComposing: true });

describe("Combobox during IME composition", () => {
  it.each([13, 229])(
    "ignores a composing Enter (keyCode %i) for a custom draft, then commits on the next Enter",
    (keyCode) => {
      const onValueChange = vi.fn();
      render(
        <Combobox
          options={options}
          value="2016-08"
          onValueChange={onValueChange}
          allowCustom
          triggerOn="blur"
        />,
      );
      const input = screen.getByRole("combobox");
      input.focus();
      compose(input, "2016-10");

      composingEnter(input, keyCode);
      expect(onValueChange).not.toHaveBeenCalled();
      expect(input).toHaveFocus();
      expect(input).toHaveValue("2016-10");

      fireEvent.compositionEnd(input);
      fireEvent.keyDown(input, { key: "Enter", keyCode: 13 });
      expect(onValueChange).toHaveBeenCalledExactlyOnceWith("2016-10");
    },
  );

  it("does not select a highlighted suggestion or move it while composing", () => {
    const onValueChange = vi.fn();
    render(
      <Combobox
        options={options}
        value=""
        onValueChange={onValueChange}
        allowCustom
        triggerOn="blur"
      />,
    );
    const input = screen.getByRole("combobox");
    input.focus();
    fireEvent.keyDown(input, { key: "ArrowDown", keyCode: 40 });
    const active = input.getAttribute("aria-activedescendant");
    expect(active).toBeTruthy();

    fireEvent.keyDown(input, {
      key: "ArrowDown",
      keyCode: 229,
      isComposing: true,
    });
    composingEnter(input);
    fireEvent.keyDown(input, { key: "Escape", isComposing: true });
    expect(onValueChange).not.toHaveBeenCalled();
    expect(input).toHaveAttribute("aria-activedescendant", active);
    expect(input).toHaveAttribute("aria-expanded", "true");

    fireEvent.keyDown(input, { key: "Escape", keyCode: 27 });
    expect(input).toHaveAttribute("aria-expanded", "false");
  });

  it("keeps the ledger Time filter at its applied value until an ordinary Enter", () => {
    const onChange = vi.fn();
    render(
      <SearchControlCombobox
        items={["2016-08", "2016-09"]}
        selected="2016-08"
        onChange={onChange}
        placeholder="期間"
        allowCustom
        triggerOn="blur"
      />,
    );
    const input = screen.getByPlaceholderText("期間");
    input.focus();
    compose(input, "2016-09");

    composingEnter(input);
    expect(onChange).not.toHaveBeenCalled();
    expect(input).toHaveFocus();

    fireEvent.compositionEnd(input);
    fireEvent.keyDown(input, { key: "Enter", keyCode: 13 });
    expect(onChange).toHaveBeenCalledWith("2016-09");
  });
});
