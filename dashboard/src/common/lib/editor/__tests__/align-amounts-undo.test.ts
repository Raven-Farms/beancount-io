import { describe, expect, it } from "vitest";
import type * as monaco from "monaco-editor";
import { alignAmounts } from "../monaco-beancount-actions";

/**
 * An editor with Monaco's documented Undo history (monaco.d.ts,
 * `executeEdits`/`pushUndoStop`): typing and `executeEdits` join the open
 * Undo group, `pushUndoStop` closes it, and Undo first closes whatever is
 * open. The real editor's history is exercised in the browser check (w4/969).
 */
function editorWithHistory(initial: string) {
  let value = initial;
  let open: { before: string } | null = null;
  const done: { before: string; after: string }[] = [];
  const undone: { before: string; after: string }[] = [];
  const record = (next: string) => {
    if (!open) open = { before: value };
    value = next;
    undone.length = 0;
  };
  const close = () => {
    if (open && open.before !== value)
      done.push({ before: open.before, after: value });
    open = null;
  };
  const lines = () => value.split("\n");
  const model = {
    getValue: () => value,
    getLineCount: () => lines().length,
    getLineContent: (line: number) => lines()[line - 1] ?? "",
    getFullModelRange: () => ({}),
  };
  const editor = {
    getModel: () => model,
    executeEdits: (_source: string, edits: { text: string }[]) =>
      record(edits[0]!.text),
    pushUndoStop: close,
  };
  return {
    editor: editor as unknown as monaco.editor.IStandaloneCodeEditor,
    type: (text: string) => record(value + text),
    undo: () => {
      close();
      const step = done.pop();
      if (step) {
        value = step.before;
        undone.push(step);
      }
    },
    redo: () => {
      const step = undone.pop();
      if (step) {
        value = step.after;
        done.push(step);
      }
    },
    value: () => value,
  };
}

const SOURCE = [
  '2024-01-01 * "Coffee"',
  "  Assets:Checking  -4.50 USD",
  "  Expenses:Food  4.50 USD",
  "",
].join("\n");
const COMMENT = "; qa-969 align-undo-control";

describe("Align Amounts keeps its own Undo step", () => {
  it("undoes only the alignment, keeping the comment typed before it", () => {
    const history = editorWithHistory(SOURCE);
    history.type(COMMENT);
    alignAmounts(history.editor);
    const aligned = history.value();
    expect(aligned).not.toBe(SOURCE + COMMENT);
    expect(aligned).toContain(COMMENT);

    history.undo();
    expect(history.value()).toBe(SOURCE + COMMENT);
    history.redo();
    expect(history.value()).toBe(aligned);
  });

  it("keeps typing after the alignment in a step of its own", () => {
    const history = editorWithHistory(SOURCE);
    alignAmounts(history.editor);
    const aligned = history.value();
    history.type(COMMENT);

    history.undo();
    expect(history.value()).toBe(aligned);
    history.undo();
    expect(history.value()).toBe(SOURCE);
  });

  it("adds no step when there is nothing to align", () => {
    const history = editorWithHistory("; nothing to align\n");
    history.type(COMMENT);
    alignAmounts(history.editor);
    expect(history.value()).toBe(`; nothing to align\n${COMMENT}`);

    history.undo();
    expect(history.value()).toBe("; nothing to align\n");
  });
});
