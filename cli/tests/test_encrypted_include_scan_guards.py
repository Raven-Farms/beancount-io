"""Ciphertext is opaque to text scans and guards unknown encrypted includes (w5/671)."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = 'include "priv/secret.bean.gpg"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n'
CHILD = '2024-01-03 * "Hidden child"\n  Expenses:Food 10 USD\n  Assets:Cash\n'
# A deterministic stand-in for a large binary ciphertext. Its raw bytes would
# trigger both the old NFC scan and the parser's quoted-string UTF-8 error.
# Only the fake gpg's valid plaintext belongs to the ledger.
CIPHERTEXT = (
    b"; opaque encrypted payload\n" * 1024
    + '2024-01-01 open Assets:Cafe\u0301\n2024-01-02 * "opaque" #cafe\u0301\n'.encode()
    + b'2024-01-02 * "opaque \xff bytes"\n  Expenses:Food 1 USD\n  Assets:Cash\n'
)


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "priv/more").mkdir(parents=True)
    (tmp_path / "bin").mkdir()
    plaintext = 'include "more/*.bean"\n' + "".join(
        f'2024-01-02 * "Secret {index}"\n  Expenses:Food 1 USD\n  Assets:Cash\n' for index in range(1200)
    )
    plain = tmp_path / "plain.txt"
    plain.write_text(plaintext)
    gpg = tmp_path / "bin/gpg"
    gpg.write_text(f"#!/bin/sh\nexec /bin/cat {shlex.quote(str(plain))}\n")
    gpg.chmod(0o755)
    (tmp_path / "main.bean").write_text(MAIN)
    (tmp_path / "priv/secret.bean.gpg").write_bytes(CIPHERTEXT)
    (tmp_path / "priv/more/a.bean").write_text(CHILD)
    return tmp_path


def _run(
    books: Path, *args: str, module: str = "cli.main", cache: str | None = None
) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        PATH=f"{books / 'bin'}{os.pathsep}{os.environ['PATH']}",
        BEA_CONFIG_DIR=str(books / "config"),
        BEA_ENGINE_DIR=str(books / "engine"),
        BEA_NO_UPDATE_NOTIFIER="1",
        XDG_CACHE_HOME=str(books / "cache"),
        XDG_DATA_HOME=str(books / "data"),
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    if cache is not None:
        env["BEANCOUNT_LOAD_CACHE_FILENAME"] = cache
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=books,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _snapshot(books: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(books)): path.read_bytes()
        for path in books.rglob("*")
        if path.is_file() and path.suffix in {".bean", ".gpg"}
    }


def _assert_encrypted_refusal(result: subprocess.CompletedProcess[str], destination: str) -> None:
    screen = result.stdout + result.stderr
    assert result.returncode == 2, screen
    assert "encrypted" in screen.lower(), screen
    assert "secret.bean.gpg" in screen
    assert destination in screen
    assert "outside" in screen.lower(), screen
    assert "Traceback" not in screen


def test_the_large_encrypted_fixture_loads_its_plaintext_and_child(books: Path) -> None:
    before = _snapshot(books)
    result = _run(books, "-f", "main.bean", "query", "SELECT count(*) AS n")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "2402" in result.stdout.split(), result.stdout
    assert _snapshot(books) == before


@pytest.mark.parametrize("operation", ["print-options", "roundtrip", "missing-open", "display-context", "directories"])
def test_doctor_never_treats_large_ciphertext_as_source_text(books: Path, operation: str) -> None:
    before = _snapshot(books)
    result = _run(books, "doctor", operation, "main.bean")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stdout + result.stderr
    assert "Re-save the file as UTF-8" not in result.stdout + result.stderr
    assert _snapshot(books) == before


@pytest.mark.parametrize("flag", ["-v", "--json", "--auto"], ids=["verbose", "native-json", "auto"])
def test_native_check_options_ignore_ciphertext_account_and_tag_spelling(books: Path, flag: str) -> None:
    before = _snapshot(books)
    result = _run(books, "-f", "main.bean", "check", flag)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Unicode NFC" not in result.stdout + result.stderr
    assert "Traceback" not in result.stdout + result.stderr
    assert _snapshot(books) == before


def test_doctor_context_refuses_a_location_in_an_encrypted_member(books: Path) -> None:
    before = _snapshot(books)
    result = _run(books, "doctor", "context", "main.bean", "priv/secret.bean.gpg:2")

    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    assert "encrypted" in result.stderr.lower()
    assert "secret.bean.gpg" in result.stderr
    assert "Traceback" not in result.stderr
    assert len(result.stderr.strip().splitlines()) == 1, result.stderr
    assert _snapshot(books) == before


@pytest.mark.parametrize("surface", ["cache-option", "cache-env", "query-file", "query-source"])
@pytest.mark.parametrize("linked", [False, True], ids=["plain-dir", "symlink-dir"])
def test_frontend_refuses_destinations_below_an_encrypted_member(books: Path, surface: str, linked: bool) -> None:
    if linked:
        (books / "priv/more").rename(books / "outside")
        (books / "priv/more").symlink_to(books / "outside", target_is_directory=True)
    before = _snapshot(books)
    if surface == "cache-option":
        destination = "priv/more/zcache.bean"
        result = _run(books, "-f", "main.bean", "check", "--cache-filename", destination)
    elif surface == "cache-env":
        destination = "priv/more/envcache.bean"
        result = _run(books, "-f", "main.bean", "balance", cache=destination)
    else:
        destination = "priv/more/backup.bean"
        args = ["-f", "main.bean", "query"] if surface == "query-file" else ["query", "--source", "main.bean"]
        result = _run(books, *args, "PRINT", "-o", destination)

    _assert_encrypted_refusal(result, destination)
    assert _snapshot(books) == before
    assert not (books / destination).exists()


@pytest.mark.parametrize("surface", ["cache-env", "query-file", "query-source"])
@pytest.mark.parametrize("linked", [False, True], ids=["plain-dir", "symlink-dir"])
def test_engine_also_refuses_destinations_below_an_encrypted_member(books: Path, surface: str, linked: bool) -> None:
    if linked:
        (books / "priv/more").rename(books / "outside")
        (books / "priv/more").symlink_to(books / "outside", target_is_directory=True)
    before = _snapshot(books)
    if surface == "cache-env":
        destination = "priv/more/envcache.bean"
        result = _run(books, "check", "--file", "main.bean", module="bea_engine", cache=destination)
    else:
        destination = "priv/more/backup.bean"
        args = (
            ["query", "--file", "main.bean", "--format", "beancount"]
            if surface == "query-file"
            else ["source-query", "main.bean"]
        )
        result = _run(books, *args, "PRINT", "--output", destination, module="bea_engine")

    _assert_encrypted_refusal(result, destination)
    assert _snapshot(books) == before
    assert not (books / destination).exists()


def test_engine_preserves_the_encrypted_guard_when_an_output_link_moves_during_load(books: Path) -> None:
    link = books / "rootlink"
    protected = books / "priv/more/backup.bean"
    safe = books / "safe.bean"
    link.symlink_to(protected)
    # text_answer approves and freezes the output target before loading. The
    # decryptor moves its original spelling during that real load, so checking
    # only the spelling would overlook the protected target still being used.
    (books / "bin/gpg").write_text(
        "#!/bin/sh\n"
        f"/bin/rm -f {shlex.quote(str(link))}\n"
        f"/bin/ln -s {shlex.quote(str(safe))} {shlex.quote(str(link))}\n"
        f"exec /bin/cat {shlex.quote(str(books / 'plain.txt'))}\n"
    )
    before = _snapshot(books)
    result = _run(
        books,
        "query",
        "--file",
        "main.bean",
        "--format",
        "beancount",
        "PRINT",
        "--output",
        "rootlink",
        module="bea_engine",
    )

    _assert_encrypted_refusal(result, "priv/more/backup.bean")
    assert link.readlink() == safe, "the decryptor must have moved the link during the load"
    assert not protected.exists()
    assert not safe.exists()
    assert _snapshot(books) == before


@pytest.mark.parametrize("surface", ["cache-option", "cache-env", "query"])
def test_destinations_outside_the_encrypted_directory_remain_usable(books: Path, surface: str) -> None:
    before = _snapshot(books)
    if surface == "cache-option":
        result = _run(books, "-f", "main.bean", "check", "--cache-filename", "safe.cache")
    elif surface == "cache-env":
        result = _run(books, "-f", "main.bean", "balance", cache="safe.cache")
    else:
        result = _run(books, "-f", "main.bean", "query", "PRINT", "-o", "safe.bean")
        assert '"Secret 0"' in (books / "safe.bean").read_text()
        assert '"Hidden child"' in (books / "safe.bean").read_text()

    assert result.returncode == 0, result.stdout + result.stderr
    assert {name: data for name, data in _snapshot(books).items() if name != "safe.bean"} == before


def test_a_native_csv_source_is_not_encrypted_by_its_filename_suffix(books: Path) -> None:
    source = books / "t.gpg"
    source.write_text("n\n73\n")
    before = source.read_bytes()
    result = _run(books, "query", "--source", "csv:t.gpg", "SELECT n FROM t", "--output", "safe.txt")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "73" in (books / "safe.txt").read_text().split()
    assert source.read_bytes() == before
