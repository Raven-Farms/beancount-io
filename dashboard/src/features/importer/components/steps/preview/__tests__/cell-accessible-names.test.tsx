import { cleanup, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createInstance, type i18n as I18nInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Table, TableBody } from "@/common/components/ui/table";
import { en, de } from "@/i18n/locales";
import { EditablePreviewRow } from "../editable-preview-row";
import { buildParsedRow } from "../../../../utils/csv-validator";
import { useCSVParser } from "../../../../hooks/use-csv-parser";
import { ImportPreviewTable } from "../import-preview-table";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");

let i18n: I18nInstance = createInstance();

beforeEach(async () => {
  i18n = createInstance();
  await i18n.init({
    lng: "en",
    fallbackLng: "en",
    resources: { en: { translation: en }, de: { translation: de } },
    interpolation: { escapeValue: false, prefix: "{", suffix: "}" },
  });
});
afterEach(cleanup);

function renderFixtureRow() {
  return render(
    <I18nextProvider i18n={i18n}>
      <Table>
        <TableBody>
          <EditablePreviewRow
            row={buildParsedRow({
              date: "2026-09-05",
              payee: "qa-20261017-plain",
              description: "qa-20261017 plain control",
              amountInput: "-3.21",
            })}
            index={0}
            onChange={vi.fn()}
            onDelete={vi.fn()}
          />
        </TableBody>
      </Table>
    </I18nextProvider>,
  );
}

describe("Smart Import preview cell accessible names", () => {
  it("names collapsed cells by column and row, not placeholder (en)", async () => {
    renderFixtureRow();

    expect(
      await screen.findByRole("button", {
        name: "Edit Date, row 1. Current value: 9/5/2026",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Edit Payee, row 1. Current value: qa-20261017-plain",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Edit Description, row 1. Current value: qa-20261017 plain control",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Edit Amount, row 1. Current value: -3.21",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Delete row 1" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Edit 0\.00/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Edit YYYY-MM-DD/ }),
    ).not.toBeInTheDocument();
  });

  it("names the open editor by column and row, keeping placeholder as hint (en)", async () => {
    const user = userEvent.setup();
    renderFixtureRow();

    await user.click(
      screen.getByRole("button", {
        name: "Edit Amount, row 1. Current value: -3.21",
      }),
    );
    const amountInput = screen.getByRole("textbox", { name: "Amount, row 1" });
    expect(amountInput).toHaveValue("-3.21");
    expect(amountInput).toHaveAttribute("placeholder", "0.00");
    expect(
      screen.queryByRole("textbox", { name: "0.00" }),
    ).not.toBeInTheDocument();

    await user.keyboard("{Escape}");
    await user.click(
      screen.getByRole("button", {
        name: "Edit Date, row 1. Current value: 9/5/2026",
      }),
    );
    const dateInput = screen.getByRole("textbox", { name: "Date, row 1" });
    expect(dateInput).toHaveAttribute("placeholder", "YYYY-MM-DD");
  });

  it("names cells by the localized column and row (de)", async () => {
    await i18n.changeLanguage("de");
    const user = userEvent.setup();
    renderFixtureRow();

    await user.click(
      screen.getByRole("button", {
        name: "Bearbeiten Sie Betrag, Zeile 1. Aktueller Wert: -3.21",
      }),
    );
    expect(
      screen.getByRole("textbox", { name: "Betrag, Zeile 1" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Zeile 1 löschen" }),
    ).toBeInTheDocument();
  });
});

/**
 * The collapsed cell's name carries the value it shows: the normalized
 * amount and the localized date, not the bank's raw token (w4/245).
 */
describe("Smart Import preview names the displayed value", () => {
  it("names comma-decimal amounts and dates as the preview shows them", async () => {
    const user = userEvent.setup();
    const { result } = renderHook(() => useCSVParser());
    const parsed = result.current.parseCSV(
      [
        "Date;Payee;Description;Amount",
        "2026-10-20;qa-eu-credit;grouped credit;2.500,00",
        "2026-10-20;qa-eu-fee;comma fee;-4,50",
        "2026-10-20;qa-eu-debit;grouped debit;-1.000",
      ].join("\n"),
    );
    render(
      <I18nextProvider i18n={i18n}>
        <ImportPreviewTable result={parsed} onResultChange={vi.fn()} />
      </I18nextProvider>,
    );

    for (const [row, shown] of [
      [1, "2500.00"],
      [2, "-4.50"],
      [3, "-1000"],
    ] as const) {
      expect(
        screen.getByRole("button", {
          name: `Edit Amount, row ${row}. Current value: ${shown}`,
        }),
      ).toHaveTextContent(shown);
    }
    expect(
      screen.getByRole("button", {
        name: "Edit Date, row 3. Current value: 10/20/2026",
      }),
    ).toHaveTextContent("10/20/2026");

    await user.click(
      screen.getByRole("button", {
        name: "Edit Amount, row 3. Current value: -1000",
      }),
    );
    expect(screen.getByRole("textbox", { name: "Amount, row 3" })).toHaveValue(
      "-1.000",
    );
  });
});
