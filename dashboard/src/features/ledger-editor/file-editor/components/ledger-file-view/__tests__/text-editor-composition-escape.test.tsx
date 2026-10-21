import { fireEvent, render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Escape during a Monaco composition cancels the composition, not the edit
 * (w4/291). Monaco's native EditContext host reports that Escape with
 * isComposing=false, so the editor's own composition lifecycle decides.
 */
function makeEditor() {
  const listeners = { start: [] as (() => void)[], end: [] as (() => void)[] };
  let findRevealed = false;
  return {
    listeners,
    setFindRevealed: (value: boolean) => {
      findRevealed = value;
    },
    instance: {
      onDidCompositionStart: vi.fn((listener: () => void) => {
        listeners.start.push(listener);
        return { dispose: vi.fn() };
      }),
      onDidCompositionEnd: vi.fn((listener: () => void) => {
        listeners.end.push(listener);
        return { dispose: vi.fn() };
      }),
      getContribution: () => ({
        getState: () => ({ isRevealed: findRevealed }),
      }),
      revealLine: vi.fn(),
      revealLineInCenter: vi.fn(),
      setPosition: vi.fn(),
      focus: vi.fn(),
      deltaDecorations: vi.fn(() => []),
      onDidScrollChange: vi.fn(),
      getVisibleRanges: vi.fn(() => []),
      getDomNode: vi.fn(() => null),
      getModel: vi.fn(() => ({
        getLineCount: () => 1,
        getLineMaxColumn: () => 1,
      })),
    },
  };
}

let current = makeEditor();
const monaco = {
  Range: class {},
  editor: { setModelLanguage: vi.fn(), setModelMarkers: vi.fn() },
};

vi.mock("@/common/components/monaco-editor", async () => {
  const { useEffect } = await import("react");
  return {
    MonacoEditor: ({
      onMount,
    }: {
      onMount: (editor: unknown, monaco: unknown) => void;
    }) => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      useEffect(() => onMount(current.instance, monaco), []);
      return <div data-testid="editor" />;
    },
  };
});
vi.mock("@/common/hooks/use-theme", () => ({ useIsDarkTheme: () => false }));
vi.mock("@/common/lib/editor/monaco-beancount-language-vscode", () => ({
  registerBeancountLanguage: vi.fn(),
}));
vi.mock("@/common/lib/editor/monaco-beancount-actions", () => ({
  registerEditorShortcuts: vi.fn(),
}));

import { TextEditor } from "../text-editor";

const escape = (init: KeyboardEventInit = {}) =>
  fireEvent.keyDown(document.body, { key: "Escape", keyCode: 27, ...init });
const compose = (phase: "start" | "end") =>
  current.listeners[phase].forEach((listener) => listener());

describe("TextEditor Escape during composition", () => {
  const onCancel = vi.fn();
  beforeEach(() => {
    onCancel.mockClear();
    current = makeEditor();
  });

  it("leaves Escape to an active composition even when the key says it is not composing", () => {
    render(<TextEditor content="" filename="main.bean" onCancel={onCancel} />);

    compose("start");
    escape();
    expect(onCancel).not.toHaveBeenCalled();

    compose("end");
    escape();
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("also honours the key's own composing flag", () => {
    render(<TextEditor content="" filename="main.bean" onCancel={onCancel} />);

    escape({ isComposing: true });
    escape({ keyCode: 229 });
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("keeps Find's Escape and read-only mode", () => {
    const view = render(
      <TextEditor content="" filename="main.bean" onCancel={onCancel} />,
    );
    current.setFindRevealed(true);
    escape();
    expect(onCancel).not.toHaveBeenCalled();

    current.setFindRevealed(false);
    view.rerender(
      <TextEditor
        content=""
        filename="main.bean"
        onCancel={onCancel}
        readOnly
      />,
    );
    escape();
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("starts a remounted editor outside any composition", () => {
    const first = render(
      <TextEditor content="" filename="main.bean" onCancel={onCancel} />,
    );
    compose("start");
    first.unmount();

    current = makeEditor();
    render(<TextEditor content="" filename="main.bean" onCancel={onCancel} />);
    escape();
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
