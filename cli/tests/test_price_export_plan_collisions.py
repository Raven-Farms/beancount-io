"""Portable exports never map two sources onto one destination (w5/652)."""

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


@pytest.mark.parametrize("shared", ["_shared", "_SHARED"])
@pytest.mark.parametrize("external_first", [False, True])
def test_external_includes_avoid_all_internal_destinations(tmp_path: Path, shared: str, external_first: bool) -> None:
    books = tmp_path / "books"
    (books / shared).mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    internal = books / shared / "01-acc.bean"
    internal.write_text("2026-01-01 open Assets:Internal USD\n")
    external = outside / "acc.bean"
    external.write_text("2026-01-01 open Assets:External USD\n")
    includes = [f'include "{shared}/01-acc.bean"\n', 'include "../outside/acc.bean"\n']
    if external_first:
        includes.reverse()
    root = books / "main.bean"
    root.write_text(
        'option "operating_currency" "USD"\n'
        + "".join(includes)
        + '2026-01-02 * "Transfer"\n  Assets:Internal  1 USD\n  Assets:External\n'
    )
    before = {path: path.read_bytes() for path in (root, internal, external)}
    out = tmp_path / "snapshot"

    result = runner.invoke(app, ["--json", "--file", str(root), "price", "export", "-o", str(out)])

    assert result.exit_code == 0, result.output
    files = json.loads(result.stdout)["data"]["files"]
    assert len(files) == len(set(files)) == 3
    assert (out / shared / "01-acc.bean").read_bytes() == before[internal]
    assert (out / "_shared/02-acc.bean").read_bytes() == before[external]
    checked = runner.invoke(app, ["--json", "--file", str(out / "main.bean"), "check"])
    assert checked.exit_code == 0, checked.output
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("link", ["symlink", "hardlink"])
def test_force_export_refuses_destinations_aliasing_each_other(tmp_path: Path, link: str) -> None:
    books = tmp_path / "books"
    (books / "txns").mkdir(parents=True)
    root = books / "main.bean"
    root.write_text('2026-01-01 open Assets:Cash USD\ninclude "txns/*.bean"\n')
    leaf = books / "txns/2026.bean"
    leaf.write_text('2026-01-02 * "Move"\n  Assets:Cash 1 USD\n  Assets:Cash -1 USD\n')
    out = tmp_path / "snapshot"
    (out / "txns").mkdir(parents=True)
    (out / "main.bean").write_text("KEEP SNAPSHOT\n")
    destination = out / "txns/2026.bean"
    if link == "symlink":
        destination.symlink_to("../main.bean")
    else:
        os.link(out / "main.bean", destination)
    before = {path: path.read_bytes() for path in (root, leaf, out / "main.bean", destination)}

    result = runner.invoke(app, ["--json", "--file", str(root), "price", "export", "-o", str(out), "--force"])

    assert result.exit_code == 2, result.output
    assert "same destination" in result.output
    assert {path: path.read_bytes() for path in before} == before
