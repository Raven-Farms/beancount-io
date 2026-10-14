"""Only the forward to bean-price refuses `--json`; the docs and the refusal say so (w5/280).

`docs/USAGE.md` listed `price` among the commands that "reject JSON mode" and
left `price status`, `refresh` and `export` out of its structured-results
list, while `--json price status` and `--json price export` answer with the
envelope. The refusal itself read as if no `price` form had JSON.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _ledger(tmp_path: Path) -> Path:
    ledger = tmp_path / "a.bean"
    ledger.write_text("2026-01-01 open Assets:A\n", encoding="utf-8")
    return ledger


def _json_section() -> str:
    usage = (ROOT / "docs" / "USAGE.md").read_text(encoding="utf-8")
    return " ".join(usage.split("\n## JSON output\n", 1)[1].split("\n## ", 1)[0].split())


def test_forward_refusal_names_the_forms_that_do_have_json(tmp_path: Path) -> None:
    result = _bea(tmp_path, "--json", "-f", str(_ledger(tmp_path)), "price", "./quotes")
    assert result.returncode == 2, result.stderr
    assert result.stdout == ""
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage"
    assert "bea price has no JSON output when it forwards to bean-price." in error["message"]
    assert "bea price status, refresh and export answer in JSON" in error["message"]


def test_status_and_export_answer_with_the_envelope(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)

    status = _bea(tmp_path, "--json", "-f", str(ledger), "price", "status")
    assert status.returncode == 0, status.stderr
    assert json.loads(status.stdout)["data"] == {"sources": []}

    export = _bea(tmp_path, "--json", "-f", str(ledger), "price", "export", "--output", "snapshot")
    assert export.returncode == 0, export.stderr
    assert set(json.loads(export.stdout)["data"]) == {"output", "files", "overwritten", "sources"}


def test_usage_distinguishes_the_forward_from_the_subcommands() -> None:
    section = _json_section()

    refusals = section.split("Commands that cannot produce JSON keep their own shapes:", 1)[1]
    refusals = refusals.split(", `cloud login`", 1)[0]
    assert "`price` when it forwards to `bean-price` reject JSON mode" in refusals
    assert "`treeify`, `price`," not in refusals
    assert "(`price status`, `refresh` and `export` answer with the envelope)" in refusals

    structured = section.split("Global `--json` provides structured results for", 1)[1].split("Usage failures", 1)[0]
    for command in ("price status", "price refresh", "price export"):
        assert f"`{command}`" in structured, command


def test_other_refusals_keep_their_unqualified_wording(tmp_path: Path) -> None:
    result = _bea(tmp_path, "--json", "example")
    assert result.returncode == 2, result.stderr
    assert "bea example has no JSON output. Run without --json" in json.loads(result.stderr)["error"]["message"]
