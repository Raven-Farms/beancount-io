"""Forwarded commands list the options bea itself reads out of their arguments (w5/241).

`price export`, `example` and `treeify` parse `--force` (and export's
`--output`/`--allow-errors`) by hand, so neither `--help` nor the generated
reference named them although the refusals tell the user to pass them.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HEADING = "bea options ("
NATIVE = "Native interface"

OWN_OPTIONS = [
    ("price", ["-o, --output DIR", "--allow-errors", "--force"]),
    ("example", ["--force"]),
    ("treeify", ["--force"]),
]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _own_paragraph(text: str) -> str:
    """The text between bea's own-options heading and the upstream interface."""
    assert HEADING in text, text
    return text.split(HEADING, 1)[1].split(NATIVE, 1)[0]


def _reference_section(command: str) -> str:
    reference = (ROOT / "docs/REFERENCE.md").read_text()
    return reference.split(f"### `bea {command}`\n", 1)[1].split("\n### ", 1)[0]


@pytest.mark.parametrize(("command", "options"), OWN_OPTIONS)
def test_help_lists_the_options_bea_reads_itself(tmp_path: Path, command: str, options: list[str]) -> None:
    result = _bea(tmp_path, command, "--help")
    assert result.returncode == 0, result.stderr
    paragraph = _own_paragraph(result.stdout)
    for option in options:
        assert option in paragraph
    # Upstream's interface still follows, after bea's own options.
    assert result.stdout.index(HEADING) < result.stdout.index(NATIVE)


def test_price_export_help_is_the_help_that_lists_them(tmp_path: Path) -> None:
    result = _bea(tmp_path, "price", "export", "--help")
    assert result.returncode == 0, result.stderr
    assert "--force" in _own_paragraph(result.stdout)


def test_price_export_help_names_every_option_its_refusal_names(tmp_path: Path) -> None:
    refused = _bea(tmp_path, "price", "export", "--bogus")
    assert refused.returncode == 2
    message = refused.stderr.split("got:", 1)[0]
    accepted = re.findall(r"--[a-z-]+", message)
    assert accepted == ["--output", "--allow-errors", "--force"]
    paragraph = _own_paragraph(_bea(tmp_path, "price", "--help").stdout)
    for option in accepted:
        assert option in paragraph


@pytest.mark.parametrize(("command", "options"), OWN_OPTIONS)
def test_reference_lists_the_options_bea_reads_itself(command: str, options: list[str]) -> None:
    section = _reference_section(command)
    paragraph = _own_paragraph(section)
    for option in options:
        assert option in paragraph
    if command == "price":
        assert "price export" in section


def test_commands_without_hand_parsed_options_gain_no_paragraph(tmp_path: Path) -> None:
    # `check` forwards too but reads no option of its own; `add price` declares
    # its `--force`, so the ordinary options table already lists it.
    check = _bea(tmp_path, "check", "--help")
    assert check.returncode == 0, check.stderr
    assert HEADING not in check.stdout
    assert NATIVE in check.stdout
    assert HEADING not in _reference_section("check")
    declared = _bea(tmp_path, "add", "price", "--help")
    assert declared.returncode == 0, declared.stderr
    assert "--force" in declared.stdout
    assert HEADING not in declared.stdout
