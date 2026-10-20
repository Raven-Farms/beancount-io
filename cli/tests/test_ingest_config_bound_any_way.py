"""`bea ingest` refuses a CONFIG module however it binds CONFIG (w5/635).

The preflight read only module-level assignments, and searched the raw text
for `Ingest(`: a module that imports `CONFIG`, binds it inside `try`, or
mentions `beangulp.Ingest(CONFIG)()` in a comment ran as an ingest script,
did nothing and exited 0.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.commands.ingest import _refuse_config_only_script
from cli.errors import UsageError
from cli.main import app

REFUSAL = "looks like a `bea import --config` module (CONFIG = [...])"


@pytest.mark.parametrize(
    "text",
    [
        "from myimps import CONFIG\n",
        "import myimps.CONFIG as CONFIG\n",
        "try:\n    from base import Base\n    CONFIG = [Base()]\nexcept ImportError:\n    CONFIG = []\n",
        "if True:\n    with open(__file__):\n        CONFIG = []\n",
        "CONFIG = []\n# beangulp.Ingest(CONFIG)()\n",
        '"""Run as beangulp.Ingest(CONFIG)()."""\nCONFIG = []\n',
    ],
    ids=["from-import", "import-as", "try", "if-with", "comment", "docstring"],
)
def test_a_config_module_is_refused(tmp_path: Path, text: str) -> None:
    script = tmp_path / "importers.py"
    script.write_text(text)

    with pytest.raises(UsageError, match="looks like a `bea import --config` module"):
        _refuse_config_only_script(script)


@pytest.mark.parametrize(
    "text",
    [
        "import beangulp\nfrom myimps import CONFIG\nbeangulp.Ingest(CONFIG)()\n",
        "from beangulp import Ingest\nfrom myimps import CONFIG\nmain = Ingest(CONFIG)\nmain()\n",
        "from myimps import CONFIG\nfrom runner import run\nif __name__ == '__main__':\n    run(CONFIG)\n",
        "def build():\n    CONFIG = []\n    return CONFIG\n",
        "from myimps import IMPORTERS\n",
    ],
    ids=["ingest-call", "ingest-name", "main-guard", "inside-def", "other-name"],
)
def test_a_script_that_runs_something_passes(tmp_path: Path, text: str) -> None:
    script = tmp_path / "ingest.py"
    script.write_text(text)

    _refuse_config_only_script(script)


def test_extract_with_an_imported_config_exits_2(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text("2026-01-01 open Assets:Bank USD\n")
    (tmp_path / "importers.py").write_text("from myimps import CONFIG\n")
    (tmp_path / "dl").mkdir()

    result = CliRunner().invoke(
        app,
        ["--file", str(tmp_path / "main.bean"), "ingest", "extract", "--config", str(tmp_path / "importers.py")]
        + [str(tmp_path / "dl"), "-o", str(tmp_path / "out.bean")],
    )

    assert result.exit_code == 2, result.output
    assert REFUSAL in result.stderr
    assert not (tmp_path / "out.bean").exists()


SIBLING = "from base import Base\nCONFIG = [Base()]\n"


@pytest.mark.parametrize(
    ("text", "sibling"),
    [
        ("\ufeff" + SIBLING, None),
        ("from myimps import *\n", SIBLING),
        ("import beangulp\nCONFIG = []\nbeangulp.Ingest(CONFIG)\n", None),
        ("import beangulp\nCONFIG = []\ndef main():\n    beangulp.Ingest(CONFIG)()\n", None),
    ],
    ids=["bom", "star-import", "constructed-not-called", "inside-uncalled-def"],
)
def test_more_config_only_shapes_are_refused(tmp_path: Path, text: str, sibling: str | None) -> None:
    """A BOM, a star import, and an entrypoint that never runs exited 0 having written nothing (w5/851)."""
    script = tmp_path / "importers.py"
    script.write_bytes(text.encode("utf-8"))
    if sibling is not None:
        (tmp_path / "myimps.py").write_text(sibling)

    with pytest.raises(UsageError, match="looks like a `bea import --config` module"):
        _refuse_config_only_script(script)


@pytest.mark.parametrize(
    ("text", "sibling"),
    [
        ("from beangulp import Ingest as Main\nCONFIG = []\nMain(CONFIG)()\n", None),
        ("import beangulp\nCONFIG = []\ndef main():\n    beangulp.Ingest(CONFIG)()\nmain()\n", None),
        ("from myimps import *\n", "IMPORTERS = []\n"),
    ],
    ids=["aliased-entrypoint", "def-called", "star-without-config"],
)
def test_an_entrypoint_that_runs_still_passes(tmp_path: Path, text: str, sibling: str | None) -> None:
    script = tmp_path / "ingest.py"
    script.write_text(text)
    if sibling is not None:
        (tmp_path / "myimps.py").write_text(sibling)

    _refuse_config_only_script(script)


@pytest.mark.parametrize("shape", ["bom", "star"])
def test_extract_with_a_bom_or_star_config_exits_2(tmp_path: Path, shape: str) -> None:
    (tmp_path / "main.bean").write_text("2026-01-01 open Assets:Bank USD\n")
    (tmp_path / "myimps.py").write_text(SIBLING)
    script = tmp_path / f"{shape}.py"
    script.write_bytes(("\ufeff" + SIBLING).encode() if shape == "bom" else b"from myimps import *\n")
    (tmp_path / "dl").mkdir()

    result = CliRunner().invoke(
        app,
        ["--file", str(tmp_path / "main.bean"), "ingest", "extract", "--config", str(script)]
        + [str(tmp_path / "dl"), "-o", str(tmp_path / "out.bean")],
    )

    assert result.exit_code == 2, result.output
    assert REFUSAL in result.stderr
    assert not (tmp_path / "out.bean").exists()
