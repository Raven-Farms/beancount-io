import fs from "fs";
import path from "path";
import { routeText } from "../route-text";

/**
 * The trip a param takes between two screens: `router.push` percent-encodes it
 * into the URL, expo-router decodes that URL once when it parses it, and
 * the route-params hook decodes the value again (its `decodeParams` keeps the
 * raw value when that second decode throws).
 */
function throughRouter(value: string): string {
  const url = encodeURIComponent(value);
  const parsed = decodeURIComponent(url);
  try {
    return decodeURIComponent(parsed);
  } catch {
    return parsed;
  }
}

// w21/221: "50%50" came back as "50P" and "2024%20Q1" opened "2024 Q1".
describe("routeText", () => {
  const samples = [
    "QA Split 50%50 run",
    "notes/2024%20Q1.bean",
    "tax-15%2025.bean",
    "%25",
    "%E2%82%AC",
    "%50",
    "50%off",
    "100%",
    "%",
    "%%41",
    "a#b?c+d&e=f",
    "café – 日本語",
    "plain",
    "",
  ];

  it("returns exactly what was sent, through the router's double decode", () => {
    for (const sample of samples) {
      expect(throughRouter(routeText(sample))).toBe(sample);
    }
  });

  it("is what makes the difference: unescaped, literal %XX is rewritten", () => {
    expect(throughRouter("QA Split 50%50 run")).toBe("QA Split 50P run");
    expect(throughRouter("notes/2024%20Q1.bean")).toBe("notes/2024 Q1.bean");
  });

  it("leaves text without a percent sign, and a missing value, alone", () => {
    expect(routeText("notes/main.bean")).toBe("notes/main.bean");
    expect(routeText(undefined)).toBe(undefined);
  });
});

describe("the senders of free-text params", () => {
  const read = (...parts: string[]) =>
    fs
      .readFileSync(path.join(__dirname, "..", "..", ...parts), "utf8")
      .replace(/\s+/g, "");
  const sites: [string[], string[]][] = [
    [
      ["screens", "ledger-file-browser-screen", "index.tsx"],
      ["path:routeText(createdPath)", "path:routeText(entry.path)"],
    ],
    [
      ["screens", "notifications-screen", "notifications-screen.tsx"],
      ["path:routeText(err.filename!)"],
    ],
    [
      ["screens", "transaction-detail-screen", "transaction-detail-screen.tsx"],
      ['path:routeText(error.filename??"")'],
    ],
    [["common", "app-links", "resolve-app-link.ts"], ["path:routeText(path)"]],
    [
      [
        "screens",
        "multi-postings-transaction",
        "multi-postings-transaction-screen.tsx",
      ],
      ["payee:routeText(payee)", "narration:routeText(narration)"],
    ],
    [
      ["screens", "merchants-screen", "merchants-screen.tsx"],
      ["payee:routeText(item.merchant.payee)", "routeText(JSON.stringify("],
    ],
    [
      ["screens", "receipt-capture-screen", "receipt-capture-screen.tsx"],
      [
        "prefillPayee:routeText(phase.payee)",
        "prefillNarration:routeText(phase.description)",
      ],
    ],
  ];

  it("escape the text before it is pushed", () => {
    for (const [file, pieces] of sites) {
      const source = read(...file);
      for (const piece of pieces) {
        expect(source.includes(piece)).toBe(true);
      }
    }
  });
});
