#!/usr/bin/env python3
"""Tests for loopx-guard.py: each loop guard belongs to the session that armed it.

Every case runs the real script as a subprocess, the way Claude Code runs it:
`start`/`end` through a Bash tool call that carries CLAUDE_CODE_SESSION_ID, and
the Stop and SessionEnd hooks with a JSON payload on stdin.

    python3 scripts/test_loopx_guard.py
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

GUARD = pathlib.Path(__file__).resolve().parent / "loopx-guard.py"
A, B = "session-a", "session-b"


class GuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self._tmp.name)
        (self.repo / ".git").mkdir()
        self.board("w2", milestones=["m53"], notes=["089.md"])
        self.board("w5", notes=["779.md"])

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def board(self, workstream: str, milestones=(), notes=()) -> None:
        root = self.repo / ".pm" / workstream
        root.mkdir(parents=True, exist_ok=True)
        (root / "README.md").write_text(f"# {workstream}\n")
        for name in milestones:
            (root / name).mkdir()
        for name in notes:
            (root / name).write_text("note\n")

    def run_guard(self, *args: str, session: str | None = None, payload: dict | None = None):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_SESSION_ID"}
        env["CLAUDE_PROJECT_DIR"] = str(self.repo)
        if session is not None:
            env["CLAUDE_CODE_SESSION_ID"] = session
        return subprocess.run(
            [sys.executable, str(GUARD), *args],
            input=json.dumps(payload) if payload is not None else "",
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def stop(self, session: str) -> dict:
        result = self.run_guard(payload={"session_id": session, "hook_event_name": "Stop"})
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def marks(self) -> list[str]:
        directory = self.repo / ".git" / "loopx"
        return sorted(p.stem for p in directory.glob("*.json")) if directory.is_dir() else []

    def test_start_binds_to_the_calling_session_and_blocks_its_stop(self) -> None:
        self.assertIn("armed for w2", self.run_guard("start", "w2", session=A).stdout)
        decision = self.stop(A)
        self.assertEqual(decision["decision"], "block")
        self.assertIn("the next pick is w2/m53", decision["reason"])

    def test_another_session_in_the_same_checkout_is_never_blocked(self) -> None:
        # The bug this fixes: B stopped first and was held to A's loop.
        self.run_guard("start", "w2", session=A)
        self.assertEqual(self.stop(B), {})
        self.assertEqual(self.marks(), [A])
        self.assertEqual(self.stop(A)["decision"], "block")

    def test_two_sessions_run_independent_loops(self) -> None:
        self.run_guard("start", "w2", session=A)
        self.run_guard("start", "w5", session=B)
        self.assertIn("w2/m53", self.stop(A)["reason"])
        self.assertIn("w5/779.md", self.stop(B)["reason"])

    def test_start_outside_claude_code_arms_nothing(self) -> None:
        result = self.run_guard("start", "w2")
        self.assertEqual(result.returncode, 0)
        self.assertIn("not armed", result.stdout)
        self.assertEqual(self.marks(), [])
        self.assertEqual(self.stop(A), {})

    def test_end_clears_only_the_calling_session(self) -> None:
        self.run_guard("start", "w2", session=A)
        self.run_guard("start", "w5", session=B)
        self.assertIn("cleared", self.run_guard("end", session=A).stdout)
        self.assertEqual(self.stop(A), {})
        self.assertEqual(self.marks(), [B])
        self.assertIn("was not armed", self.run_guard("end", session=A).stdout)

    def test_session_end_hook_forgets_that_session(self) -> None:
        self.run_guard("start", "w2", session=A)
        self.run_guard("start", "w5", session=B)
        result = self.run_guard("forget", payload={"session_id": A, "hook_event_name": "SessionEnd"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.marks(), [B])

    def test_drained_workstream_lets_the_stop_through_and_clears_the_mark(self) -> None:
        self.run_guard("start", "w2", session=A)
        (self.repo / ".pm" / "w2" / "m53").rmdir()
        (self.repo / ".pm" / "w2" / "089.md").unlink()
        self.assertEqual(self.stop(A), {})
        self.assertEqual(self.marks(), [])

    def test_stands_down_after_repeated_stops_without_progress(self) -> None:
        self.run_guard("start", "w2", session=A)
        for _ in range(25):
            self.assertEqual(self.stop(A)["decision"], "block")
        final = self.stop(A)
        self.assertNotIn("decision", final)
        self.assertIn("stood down", final["systemMessage"])

    def test_progress_resets_the_spin_counter(self) -> None:
        self.run_guard("start", "w2", session=A)
        for _ in range(20):
            self.stop(A)
        (self.repo / ".pm" / "w2" / "m53").rmdir()  # one item shipped
        for _ in range(20):
            self.assertEqual(self.stop(A)["decision"], "block")

    def test_unsafe_session_ids_never_touch_the_filesystem(self) -> None:
        self.assertIn("not armed", self.run_guard("start", "w2", session="../../escape").stdout)
        self.assertEqual(self.stop("../../escape"), {})
        self.assertFalse((self.repo / "escape.json").exists())
        self.assertEqual(self.marks(), [])

    def test_rejects_a_workstream_that_is_not_an_id(self) -> None:
        result = self.run_guard("start", "../w2", session=A)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.marks(), [])

    def test_unreadable_mark_is_cleared_rather_than_blocking(self) -> None:
        directory = self.repo / ".git" / "loopx"
        directory.mkdir()
        (directory / f"{A}.json").write_text("{not json")
        self.assertEqual(self.stop(A), {})
        self.assertEqual(self.marks(), [])

    def test_old_repository_wide_mark_is_ignored_and_swept(self) -> None:
        legacy = self.repo / ".git" / "loopx-active.json"
        legacy.write_text(json.dumps({"workstream": "w2", "session_id": B, "blocks": 0}))
        self.assertEqual(self.stop(B), {})
        self.run_guard("start", "w5", session=A)
        self.assertFalse(legacy.exists())

    def test_start_sweeps_marks_left_by_crashed_sessions(self) -> None:
        self.run_guard("start", "w2", session=B)
        old = time.time() - 8 * 24 * 3600
        os.utime(self.repo / ".git" / "loopx" / f"{B}.json", (old, old))
        self.run_guard("start", "w5", session=A)
        self.assertEqual(self.marks(), [A])


if __name__ == "__main__":
    unittest.main()
