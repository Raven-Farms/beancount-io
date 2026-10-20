#!/usr/bin/env python3
"""Keep `/loopx` running while its workstream still has actionable work.

The rule — never stop while a next pick exists — is stated four times in
`.agents/skills/loopx/SKILL.md`, and was still broken once: the loop wrote an
end-of-run summary and treated writing it as a turn boundary, naming the next
pick in the same breath. Prose cannot enforce itself. This can.

Each mark belongs to the Claude Code session that armed it: `start` reads the
caller's `CLAUDE_CODE_SESSION_ID`, and the Stop hook consults only the mark of
the session that is stopping. Several sessions can therefore share one
checkout, each running its own loop or none, without blocking each other. (An
earlier version kept one mark per repository and bound it to whichever session
stopped first, so an unrelated session was held to a loop it never started
while the real loop lost its guard.)

Four modes:

    loopx-guard.py start <wN>   arm a loop for the calling Claude Code session
    loopx-guard.py end          disarm the calling session's loop (a genuine Exit)
    loopx-guard.py              Stop hook: reads the hook payload on stdin and
                                blocks the stop while this session's loop has work
    loopx-guard.py forget       SessionEnd hook: drop the ending session's mark

Outside Claude Code there is no session id and no Stop hook (Codex has
neither), so `start` arms nothing and says so; the skill's exit rules still
apply there.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import time

# A stop attempt that makes no progress may repeat; bound it rather than spin.
MAX_BLOCKS_WITHOUT_PROGRESS = 25
# A mark this old belongs to a session that ended without SessionEnd (a crash).
STALE_SECONDS = 7 * 24 * 3600

SESSION_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")
WORKSTREAM = re.compile(r"w\d+")


def project_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def state_dir() -> pathlib.Path:
    """Runtime state, never project content: `.git/` is inherently untracked."""
    git = project_dir() / ".git"
    if git.is_dir():
        return git / "loopx"
    # Worktrees and odd checkouts: fall back to a per-repo temp directory.
    import hashlib
    import tempfile

    key = hashlib.sha256(str(project_dir()).encode()).hexdigest()[:16]
    return pathlib.Path(tempfile.gettempdir()) / f"loopx-{key}"


def mark_path(session: object) -> pathlib.Path | None:
    """The session's mark, or None for a missing or unsafe session id."""
    if not isinstance(session, str) or not SESSION_ID.fullmatch(session):
        return None
    return state_dir() / f"{session}.json"


def calling_session() -> pathlib.Path | None:
    return mark_path(os.environ.get("CLAUDE_CODE_SESSION_ID"))


def sweep() -> None:
    """Drop marks left by crashed sessions, and the old one-per-repo mark."""
    legacy = project_dir() / ".git" / "loopx-active.json"
    stale = [legacy]
    if state_dir().is_dir():
        cutoff = time.time() - STALE_SECONDS
        stale += [p for p in state_dir().glob("*.json") if p.stat().st_mtime < cutoff]
    for path in stale:
        try:
            path.unlink()
        except OSError:
            pass


def actionable(workstream: str) -> tuple[list[str], list[str]]:
    """Open milestones and open inbox notes, in the loop's own pick order."""
    root = project_dir() / ".pm" / workstream
    if not root.is_dir():
        return [], []
    milestones = sorted(p.name for p in root.glob("m*") if p.is_dir())
    notes = sorted(
        p.name for p in root.glob("*.md") if p.name.lower() != "readme.md"
    )
    return milestones, notes


def allow(path: pathlib.Path | None = None) -> None:
    """Let the stop through, removing PATH (the session's mark) when given."""
    if path is not None:
        try:
            path.unlink()
        except OSError:
            pass
    print("{}")
    sys.exit(0)


def read_payload() -> dict:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def cmd_start(workstream: str) -> None:
    if not WORKSTREAM.fullmatch(workstream):
        print(f"loopx guard: {workstream!r} is not a workstream id like w2", file=sys.stderr)
        sys.exit(2)
    sweep()
    path = calling_session()
    if path is None:
        print(
            "loopx guard not armed: no Claude Code session id here, so no Stop hook "
            "can hold this loop. Follow the skill's exit rules."
        )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "workstream": workstream,
                "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "blocks": 0,
                "remaining": None,
            }
        )
    )
    print(f"loopx guard armed for {workstream} in this session only")


def cmd_end() -> None:
    sweep()
    path = calling_session()
    if path is not None and path.is_file():
        path.unlink()
        print("loopx guard cleared for this session")
    else:
        print("loopx guard was not armed in this session")


def cmd_forget() -> None:
    path = mark_path(read_payload().get("session_id"))
    allow(path)


def cmd_hook() -> None:
    path = mark_path(read_payload().get("session_id"))
    if path is None or not path.is_file():
        allow()  # this session runs no loop

    try:
        state = json.loads(path.read_text())
        workstream = state["workstream"]
    except Exception:
        allow(path)

    milestones, notes = actionable(workstream)
    remaining = len(milestones) + len(notes)
    if remaining == 0:
        allow(path)  # genuinely Done

    # Reset the spin counter whenever the queue actually got shorter.
    previous = state.get("remaining")
    blocks = 0 if previous is None or remaining < previous else int(state.get("blocks", 0))
    blocks += 1
    if blocks > MAX_BLOCKS_WITHOUT_PROGRESS:
        # Something is wrong beyond a missed pick; let the turn end and say so.
        print(
            json.dumps(
                {
                    "systemMessage": (
                        f"loopx guard stood down after {blocks} stop attempts with no "
                        f"progress on {workstream}. Clear it with "
                        "`python3 scripts/loopx-guard.py end`."
                    )
                }
            )
        )
        sys.exit(0)

    state["blocks"] = blocks
    state["remaining"] = remaining
    try:
        path.write_text(json.dumps(state))
    except OSError:
        pass

    nxt = f"{workstream}/{milestones[0]}" if milestones else f"{workstream}/{notes[0]}"
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    f"/loopx {workstream} is still running: {remaining} item(s) remain "
                    f"and the next pick is {nxt}. This is not one of the three exits — "
                    "nothing is blocked and a progress summary is not an exit. Pick "
                    f"{nxt}, triage it on evidence, and continue. If every remaining "
                    "item really is blocked, move them with /pm block; when the loop "
                    "genuinely ends, run `python3 scripts/loopx-guard.py end`."
                ),
            }
        )
    )


def main() -> None:
    args = sys.argv[1:]
    if not args:
        cmd_hook()
    elif args[0] == "start" and len(args) == 2:
        cmd_start(args[1])
    elif args == ["end"]:
        cmd_end()
    elif args == ["forget"]:
        cmd_forget()
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
