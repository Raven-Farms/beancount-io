"""`--strict-prices doctor roundtrip` fails with the strict error, not a traceback (w5/643).

The managed load raised bea's strict error inside upstream's roundtrip, whose
`finally` then called `os.path.exists(None)`: the TypeError replaced it, and
`doctor roundtrip` printed a 200-line traceback where every other doctor
command printed one line.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

STRICT = "error: managed price source https://beancount.io/prices/BTC-USD is unavailable in strict mode"


@pytest.mark.parametrize("op", ["roundtrip", "missing-open"])
def test_a_strict_failure_is_one_line(tmp_path: Path, bea_config_dir: Path, op: str) -> None:
    books = tmp_path / "books"
    books.mkdir()
    ledger = books / "main.bean"
    ledger.write_text(
        'option "operating_currency" "USD"\ninclude "https://beancount.io/prices/BTC-USD"\n'
        "2020-01-01 open Assets:Cash USD\n"
    )

    result = CliRunner().invoke(app, ["--offline", "--strict-prices", "doctor", op, str(ledger)])

    assert result.exit_code == 1, result.output
    assert result.stderr.strip().splitlines()[-1].startswith(STRICT)
    assert "Traceback" not in result.stderr and "TypeError" not in result.stderr
    # Nothing of upstream's roundtrip scratch is left beside the ledger.
    assert [path.name for path in books.iterdir()] == ["main.bean"]
