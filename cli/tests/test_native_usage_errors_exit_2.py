"""A bad option to a forwarded upstream command is a usage error, exit 2 (w5/089).

`bea example --nosuch` and `bea treeify --nosuch` exited 1 — the
ledger/validation category — while the message itself quoted upstream's
exit 2.
"""

from __future__ import annotations

import subprocess

import pytest
from typer.testing import CliRunner

from cli.engine import launch
from cli.errors import BeaError, UsageError
from cli.main import app

runner = CliRunner()


@pytest.mark.parametrize(
    ("args", "stdin", "quoted"),
    [
        (["example", "--nosuch"], None, "bean-example failed (exit 2)"),
        (["example", "--seed", "abc"], None, "bean-example failed (exit 2)"),
        (["treeify", "--nosuch"], "x\n", "treeify failed (exit 2)"),
    ],
    ids=["example-option", "example-value", "treeify-option"],
)
def test_an_upstream_usage_error_exits_2(
    bea_config_dir: object, args: list[str], stdin: str | None, quoted: str
) -> None:
    result = runner.invoke(app, args, input=stdin)

    assert result.exit_code == 2, result.output
    assert quoted in result.output


def test_an_upstream_usage_error_is_a_usage_category(bea_config_dir: object) -> None:
    completed = subprocess.CompletedProcess(["bean-example"], 2, "", "Error: No such option '--nosuch'.\n")

    with pytest.raises(UsageError) as caught:
        launch.check_native(completed, "bean-example")

    assert caught.value.category == "usage"
    assert caught.value.exit_code == 2


@pytest.mark.parametrize(
    ("status", "stderr"),
    [
        (1, "ValueError: could not generate\n"),
        (2, "Traceback (most recent call last):\n  File x\nIndexError: list index out of range\n"),
        (3, "something else\n"),
    ],
    ids=["status-1", "crash-that-exits-2", "status-3"],
)
def test_other_upstream_failures_keep_exit_1(status: int, stderr: str) -> None:
    completed = subprocess.CompletedProcess(["bean-example"], status, "", stderr)

    with pytest.raises(BeaError) as caught:
        launch.check_native(completed, "bean-example")

    assert not isinstance(caught.value, UsageError)
    assert caught.value.exit_code == 1


def test_a_valid_example_still_generates(bea_config_dir: object) -> None:
    result = runner.invoke(app, ["example", "--date-begin", "2024-01-01", "--date-end", "2024-06-01", "--seed", "1"])

    assert result.exit_code == 0, result.output
    assert "open " in result.output
