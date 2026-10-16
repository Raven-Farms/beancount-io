"""A rewritten ledger keeps its group, ACL, extended attributes and flags (w1/099).

Writes stage a new file and rename it over the ledger, and only the mode bits
were copied across: the group fell back to the directory's (group members lost
access), a deny ACL vanished (widening read access), and xattrs and file
flags were dropped — after every add, import and `format -i`.
"""

from __future__ import annotations

import ctypes
import errno
import os
import stat
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from bea_engine.ledger import formatting, write
from bea_engine.protocol import EXIT_AUTH, AuthError

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX ownership and attributes")

LEDGER = 'option "operating_currency" "USD"\n\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food USD\n'
NOTE = '2026-01-05 note Assets:Checking "hello"\n'


def _add(file: Path) -> None:
    write.append(file, [NOTE])


def _format(file: Path) -> None:
    file.write_text(file.read_text() + '2026-01-06 * "x"\n  Expenses:Food    1 USD\n  Assets:Checking\n')
    formatting.format_files([file], in_place=True, prefix_width=None, num_width=None, currency_column=None)


WRITES: dict[str, Callable[[Path], None]] = {"add": _add, "format": _format}


def _ledger(tmp_path: Path) -> Path:
    file = tmp_path / "main.bean"
    file.write_text(LEDGER)
    return file


def _other_group(directory: Path) -> int:
    gid = directory.stat().st_gid
    for group in os.getgroups():
        if group != gid:
            return group
    pytest.skip("this user belongs to no second group to assign")


def _acl_bytes(file: Path) -> bytes | None:
    """Read the complete native ACL without resolving its principal names."""
    libc = ctypes.CDLL("libc.dylib", use_errno=True)
    libc.acl_get_file.argtypes = [ctypes.c_char_p, ctypes.c_int]
    libc.acl_get_file.restype = ctypes.c_void_p
    libc.acl_size.argtypes = [ctypes.c_void_p]
    libc.acl_size.restype = ctypes.c_ssize_t
    libc.acl_copy_ext.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ssize_t]
    libc.acl_copy_ext.restype = ctypes.c_ssize_t
    libc.acl_free.argtypes = [ctypes.c_void_p]
    libc.acl_free.restype = ctypes.c_int
    acl = libc.acl_get_file(os.fsencode(file), 0x100)  # ACL_TYPE_EXTENDED
    if not acl:
        number = ctypes.get_errno()
        if number == errno.ENOENT:
            file.stat()  # Distinguish an absent ACL from an absent file.
            return None
        raise OSError(number, os.strerror(number), file)
    try:
        size = libc.acl_size(acl)
        if size < 0:
            number = ctypes.get_errno()
            raise OSError(number, os.strerror(number), file)
        buffer = ctypes.create_string_buffer(size)
        written = libc.acl_copy_ext(buffer, acl, size)
        if written < 0:
            number = ctypes.get_errno()
            raise OSError(number, os.strerror(number), file)
        return buffer.raw[:written]
    finally:
        if libc.acl_free(acl) != 0:
            number = ctypes.get_errno()
            raise OSError(number, os.strerror(number), file)


@pytest.mark.parametrize("operation", WRITES)
def test_the_group_and_mode_survive(tmp_path: Path, operation: str) -> None:
    file = _ledger(tmp_path)
    group = _other_group(tmp_path)
    os.chown(file, -1, group)
    if file.stat().st_gid != group:
        pytest.skip("this volume ignores ownership")
    file.chmod(0o660)

    WRITES[operation](file)

    after = file.stat()
    assert after.st_gid == group
    assert stat.S_IMODE(after.st_mode) == 0o660
    assert "note Assets:Checking" in file.read_text() or operation == "format"


def test_a_group_this_user_cannot_assign_refuses_the_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Closest unprivileged stand-in for a ledger whose group the writer is not in."""
    file = _ledger(tmp_path)
    before = file.read_bytes()
    real = os.stat_result

    def foreign_group(path: Path) -> os.stat_result:
        values = list(os.stat(path))
        values[stat.ST_GID] = values[stat.ST_GID] + 1
        return real(values)

    original_stat = foreign_group(file)

    def deny(path: object, uid: int, gid: int) -> None:
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(os, "chown", deny)
    with write.candidate_file(file, before.decode() + NOTE) as candidate, pytest.raises(AuthError) as refused:
        write.keep_file_metadata(file, candidate, original_stat)

    assert refused.value.exit_code == EXIT_AUTH
    assert "group" in str(refused.value)
    assert file.read_bytes() == before


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS ACLs, xattr tool and BSD file flags")
@pytest.mark.parametrize("operation", WRITES)
def test_acl_xattrs_and_flags_survive_on_macos(tmp_path: Path, operation: str) -> None:
    file = _ledger(tmp_path)
    subprocess.run(["chmod", "+a", "user:nobody deny read", str(file)], check=True)
    subprocess.run(["xattr", "-w", "user.tag", "keep", str(file)], check=True)
    os.chflags(file, stat.UF_NODUMP)
    before_acl = _acl_bytes(file)
    assert before_acl is not None

    WRITES[operation](file)

    assert _acl_bytes(file) == before_acl
    tag = subprocess.run(["xattr", "-p", "user.tag", str(file)], check=True, capture_output=True, text=True)
    assert tag.stdout.strip() == "keep"
    assert file.stat().st_flags & stat.UF_NODUMP


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS extended ACL serialization")
def test_acl_oracle_distinguishes_principals_permissions_and_removed_acls(tmp_path: Path) -> None:
    file = _ledger(tmp_path)
    assert _acl_bytes(file) is None
    subprocess.run(["chmod", "+a", "user:nobody deny read", str(file)], check=True)
    original = _acl_bytes(file)
    assert original is not None
    assert _acl_bytes(file) == original

    subprocess.run(["chmod", "-a#", "0", str(file)], check=True)
    subprocess.run(["chmod", "+a", "user:nobody deny write", str(file)], check=True)
    assert _acl_bytes(file) != original

    subprocess.run(["chmod", "-a#", "0", str(file)], check=True)
    subprocess.run(["chmod", "+a", "user:daemon deny read", str(file)], check=True)
    assert _acl_bytes(file) != original

    subprocess.run(["chmod", "-N", str(file)], check=True)
    assert _acl_bytes(file) is None


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux user xattrs")
def test_user_xattrs_survive_on_linux(tmp_path: Path) -> None:
    file = _ledger(tmp_path)
    try:
        os.setxattr(file, "user.tag", b"keep")
    except OSError:
        pytest.skip("this filesystem does not take user xattrs")

    _add(file)

    assert os.getxattr(file, "user.tag") == b"keep"
