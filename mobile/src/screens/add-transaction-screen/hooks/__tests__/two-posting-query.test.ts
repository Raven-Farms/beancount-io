import fs from "fs";
import path from "path";
import { twoPostingSuggestionsQuery } from "../two-posting-query";

// w21/149: the raw payee was parsed as filter syntax and refused.
describe("twoPostingSuggestionsQuery", () => {
  it("quotes a payee with punctuation so the server reads it as text", () => {
    expect(twoPostingSuggestionsQuery("Dupar's")).toEqual({
      filter: `"Dupar['\u2018\u2019]s"`,
      limit: 50,
    });
    expect(twoPostingSuggestionsQuery("Mr. Marcel").filter).toBe(
      '"Mr\\. Marcel"',
    );
    expect(twoPostingSuggestionsQuery("Chase:Slate").filter).toBe(
      '"Chase:Slate"',
    );
    expect(twoPostingSuggestionsQuery("25 Degrees Burger Bar").filter).toBe(
      '"25 Degrees Burger Bar"',
    );
  });

  it("is what the hook queries with", () => {
    const hook = fs.readFileSync(
      path.join(__dirname, "..", "use-two-posting-suggestions.ts"),
      "utf8",
    );
    expect(hook.includes("query: twoPostingSuggestionsQuery(payee)")).toBe(
      true,
    );
  });
});
