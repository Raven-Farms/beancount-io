#!/usr/bin/env python3
"""Measure which customer skill Claude Code and Codex choose for each routing prompt.

Local only: every prompt is a paid client call, so CI never runs this script
(`ci-check.py` validates the routing set itself). Stdlib only.

    python3 skills/scripts/run-routing.py                    # every installed client
    python3 skills/scripts/run-routing.py --clients codex --only none-close-amex-account
    python3 skills/scripts/run-routing.py --score skills/tmp/routing/<run>/results.json

Each client runs in a scratch workspace created in the system temp directory,
outside this repository, so neither client loads this repository's own
instructions or development skills. The workspace is a fresh Git repository
holding a small synthetic ledger and links to every `beancount-*` directory
of `--suite` (default: this checkout's customer suite), linked into
`.claude/skills` and `.agents/skills` the same way the installer links them.
Results go to `skills/tmp/routing/` (gitignored).

How a choice is detected, verified against Claude Code 2.1.289 and Codex 0.163.0:

- Claude Code (`claude -p --output-format stream-json`): the first `Skill`
  tool call, whose input names the skill. Edit/Write tools are disallowed and
  no MCP server is loaded (`--strict-mcp-config`).
- Codex (`codex exec --json --sandbox read-only`): Codex has no skill tool; it
  opens a skill by running a shell command that reads `<skill>/SKILL.md`. The
  first command that reads a `SKILL.md` names the choice.

The client is stopped as soon as a choice is seen. A run that finishes without
one chose no skill. A skill outside the suite (a user-level skill or plugin)
counts as `none` for scoring; its raw name is kept in the results. The
client's user-level skills and configuration still load, as they would for a
customer.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILLS_ROOT.parent
ROUTING_SET = SKILLS_ROOT / "evals" / "routing.json"
SUITE_DIR = SKILLS_ROOT / ".claude" / "skills"
OUT_ROOT = SKILLS_ROOT / "tmp" / "routing"
CLIENTS = ("claude", "codex")

LEDGER = """\
option "title" "Synthetic routing ledger"
option "operating_currency" "USD"

2026-01-01 open Assets:Bank:Checking USD
2026-01-01 open Assets:Bank:Savings USD
2026-01-01 open Assets:Bank:OldSavings USD
2026-01-01 open Liabilities:CreditCard:Amex USD
2026-01-01 open Expenses:Food:Groceries USD
2026-01-01 open Expenses:Food:Dining USD
2026-01-01 open Expenses:Housing:Rent USD
2026-01-01 open Expenses:Subscriptions USD
2026-01-01 open Income:Salary USD
2026-01-01 open Equity:OpeningBalances USD

2026-09-01 * "LANDLORD" "September rent"
  Assets:Bank:Checking        -1200.00 USD
  Expenses:Housing:Rent        1200.00 USD

2026-09-03 * "TRADER JOES" "Groceries"
  Liabilities:CreditCard:Amex   -54.20 USD
  Expenses:Food:Groceries        54.20 USD

2026-09-12 * "NETFLIX" "Streaming"
  Liabilities:CreditCard:Amex   -17.99 USD
  Expenses:Subscriptions         17.99 USD
"""

CODEX_SKILL_READ = re.compile(r"([A-Za-z0-9._:-]+)/SKILL\.md")


def make_workspace(suite: Path) -> Path:
    workspace = Path(tempfile.mkdtemp(prefix="beancount-routing-"))
    subprocess.run(["git", "init", "-q", str(workspace)], check=True)
    (workspace / "main.bean").write_text(LEDGER, encoding="utf-8")
    for skills_dir in (workspace / ".claude" / "skills", workspace / ".agents" / "skills"):
        skills_dir.mkdir(parents=True)
        for skill in sorted(suite.glob("beancount-*/SKILL.md")):
            (skills_dir / skill.parent.name).symlink_to(skill.parent.resolve())
    return workspace


def client_version(client: str) -> str:
    try:
        out = subprocess.run([client, "--version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr) else "unknown"


def claude_command(prompt: str, model: str | None) -> list[str]:
    command = [
        "claude", "-p", prompt,
        "--output-format", "stream-json", "--verbose",
        "--max-turns", "4",
        "--strict-mcp-config",
        "--disallowedTools", "Edit", "Write", "NotebookEdit",
    ]
    return command + (["--model", model] if model else [])


def codex_command(prompt: str, model: str | None) -> list[str]:
    command = ["codex", "exec", "--json", "--sandbox", "read-only", "--skip-git-repo-check"]
    return command + (["-m", model] if model else []) + [prompt]


def claude_event(event: dict, meta: dict) -> tuple[str | None, str | None]:
    """Return (choice, error) for one Claude Code stream-json event."""
    if event.get("type") == "system" and event.get("subtype") == "init":
        meta.setdefault("model", event.get("model"))
    if event.get("type") == "assistant":
        for part in event.get("message", {}).get("content", []):
            if part.get("type") == "tool_use" and part.get("name") == "Skill":
                return str(part.get("input", {}).get("skill", "")), None
    if event.get("type") == "result" and event.get("is_error") and event.get("subtype") not in (
        "error_max_turns",
    ):
        return None, str(event.get("result") or event.get("subtype"))
    return None, None


def codex_event(event: dict, meta: dict) -> tuple[str | None, str | None]:
    """Return (choice, error) for one Codex `exec --json` event."""
    item = event.get("item", {})
    if item.get("type") == "command_execution":
        found = CODEX_SKILL_READ.search(item.get("command", ""))
        if found:
            return found.group(1), None
    if event.get("type") in ("turn.failed", "error"):
        message = event.get("message") or event.get("error", {}).get("message")
        return None, str(message)[:300]
    return None, None


def run_one(client: str, entry: dict, workspace: Path, model: str | None, timeout: float) -> dict:
    command = claude_command if client == "claude" else codex_command
    handle = claude_event if client == "claude" else codex_event
    meta: dict = {}
    started = time.monotonic()
    choice: str | None = None
    error: str | None = None
    process = subprocess.Popen(
        command(entry["prompt"], model),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        assert process.stdout is not None
        for line in process.stdout:
            if time.monotonic() - started > timeout:
                error = f"timeout after {timeout:.0f}s"
                break
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            choice, error = handle(event, meta)
            if choice is not None or error is not None:
                break
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
    return {
        "id": entry["id"],
        "client": client,
        "expected": entry["expected"],
        "chosen": choice if choice is not None else ("none" if error is None else None),
        "error": error,
        "seconds": round(time.monotonic() - started, 1),
        **({"model": meta["model"]} if meta.get("model") else {}),
    }


def normalize(choice: str | None, suite: set[str]) -> str | None:
    """Map a raw choice to a suite label: a skill outside the suite is `none`."""
    if choice is None:
        return None
    name = choice.split(":")[-1]
    return name if name in suite else "none"


def score(entries: list[dict], results: list[dict], suite: set[str]) -> dict:
    """Per client: accuracy, per-skill precision/recall, and confusion pairs.

    A result with an error (no choice observed) counts as a miss and is listed.
    """
    expected = {entry["id"]: entry["expected"] for entry in entries}
    summary: dict = {}
    for client in sorted({r["client"] for r in results}):
        rows = [r for r in results if r["client"] == client and r["id"] in expected]
        chosen = {r["id"]: normalize(r["chosen"], suite) for r in rows}
        labels = sorted(suite | {"none"})
        per_label = {}
        for label in labels:
            true_positive = sum(1 for i, c in chosen.items() if c == label and expected[i] == label)
            predicted = sum(1 for c in chosen.values() if c == label)
            actual = sum(1 for i in chosen if expected[i] == label)
            per_label[label] = {
                "precision": round(true_positive / predicted, 3) if predicted else None,
                "recall": round(true_positive / actual, 3) if actual else None,
                "support": actual,
            }
        misses = sorted(
            (i, expected[i], chosen[i] if chosen[i] is not None else "error") for i in chosen if chosen[i] != expected[i]
        )
        summary[client] = {
            "correct": len(rows) - len(misses),
            "total": len(rows),
            "per_label": per_label,
            "confusion": Counter(f"{e} -> {c}" for _, e, c in misses).most_common(),
            "misses": [{"id": i, "expected": e, "chosen": c} for i, e, c in misses],
        }
    return summary


def report(summary: dict) -> str:
    lines = []
    for client, data in summary.items():
        lines.append(f"## {client}: {data['correct']}/{data['total']} routed as labeled\n")
        lines.append("| label | precision | recall | support |")
        lines.append("| --- | --- | --- | --- |")
        for label, row in data["per_label"].items():
            fmt = lambda v: "—" if v is None else f"{v:.2f}"  # noqa: E731
            lines.append(f"| {label} | {fmt(row['precision'])} | {fmt(row['recall'])} | {row['support']} |")
        lines.append("")
        if data["misses"]:
            lines.append("| prompt id | expected | chosen |")
            lines.append("| --- | --- | --- |")
            lines.extend(f"| {m['id']} | {m['expected']} | {m['chosen']} |" for m in data["misses"])
            lines.append("")
    return "\n".join(lines)


def suite_names(suite: Path) -> set[str]:
    return {path.parent.name for path in suite.glob("beancount-*/SKILL.md")}


def revision() -> str:
    out = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--clients", default=",".join(CLIENTS), help="comma-separated: claude,codex")
    parser.add_argument("--set", type=Path, default=ROUTING_SET, help="routing set JSON")
    parser.add_argument("--suite", type=Path, default=SUITE_DIR, help="directory holding beancount-* skills")
    parser.add_argument("--only", default="", help="comma-separated entry ids to run")
    parser.add_argument("--claude-model", default=None)
    parser.add_argument("--codex-model", default=None)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=240.0, help="seconds per prompt")
    parser.add_argument("--out", type=Path, default=None, help="results directory")
    parser.add_argument("--score", type=Path, default=None, help="re-score a results.json without running")
    args = parser.parse_args(argv)

    routing = json.loads(args.set.read_text(encoding="utf-8"))
    entries = routing["entries"]
    if args.only:
        wanted = set(args.only.split(","))
        entries = [entry for entry in entries if entry["id"] in wanted]
    suite = suite_names(args.suite)

    if args.score:
        recorded = json.loads(args.score.read_text(encoding="utf-8"))
        print(report(score(entries, recorded["results"], suite)))
        return 0

    clients = []
    for client in filter(None, args.clients.split(",")):
        if client not in CLIENTS:
            parser.error(f"unknown client {client!r}")
        if shutil.which(client):
            clients.append(client)
        else:
            print(f"note: {client} is not installed; skipped", file=sys.stderr)
    if not clients:
        print("no client to run", file=sys.stderr)
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or OUT_ROOT / stamp
    out.mkdir(parents=True, exist_ok=True)
    meta = {
        "date": stamp,
        "revision": revision(),
        "suite": str(args.suite),
        "clients": {
            client: {"version": client_version(client), "model": getattr(args, f"{client}_model") or "client default"}
            for client in clients
        },
    }
    results: list[dict] = []
    workspaces = {client: make_workspace(args.suite) for client in clients}
    try:
        jobs = [(client, entry) for client in clients for entry in entries]
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            futures = [
                pool.submit(run_one, client, entry, workspaces[client], getattr(args, f"{client}_model"), args.timeout)
                for client, entry in jobs
            ]
            for future in futures:
                result = future.result()
                results.append(result)
                mark = "ok " if normalize(result["chosen"], suite) == result["expected"] else "MISS"
                print(f"{mark} {result['client']:6} {result['id']:36} -> {result['chosen'] or result['error']}")
    finally:
        for workspace in workspaces.values():
            shutil.rmtree(workspace, ignore_errors=True)

    for client in clients:
        observed = Counter(r["model"] for r in results if r["client"] == client and r.get("model"))
        if observed:
            meta["clients"][client]["observed_model"] = observed.most_common(1)[0][0]
    (out / "results.json").write_text(json.dumps({"meta": meta, "results": results}, indent=2) + "\n")
    summary = report(score(entries, results, suite))
    (out / "summary.md").write_text(f"# Routing run {stamp} at {meta['revision']}\n\n{summary}\n")
    print(f"\n{summary}\nresults: {out.relative_to(REPO_ROOT) if out.is_relative_to(REPO_ROOT) else out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
