"""Upstream compatibility shims, installed when this package is imported.

The frontend (`cli.*`) never imports this package — it reaches the engine
across a process boundary — so a shim here cannot slow or break the command
surface. Every `bea-engine` invocation imports this package first, which is
what makes one installation point cover every helper command.
"""

from __future__ import annotations

import io
import os
import unicodedata
from typing import Any

UTF8_BOM = b"\xef\xbb\xbf"
"""The three bytes several Windows editors prepend to a UTF-8 ledger."""


def install() -> None:
    """Teach Beancount's parser to skip a leading BOM and read NFC on any ledger file.

    The loader funnels the entry file and every include through
    `parser.parse_file`, so one wrapper there covers `check`, `list`,
    `query`, `report`, `add`, and `import` in a single place. A path is read
    and re-offered as a byte stream with the real filename kept for error
    reports; anything else — stdin, an open stream — passes through untouched.
    """
    from beancount.parser import parser as beancount_parser

    original = beancount_parser.parse_file
    if getattr(original, "__bea_bom_wrapped__", False):
        return

    def parse_file(file: Any, *args: Any, **kwargs: Any) -> Any:
        if file != "-" and not isinstance(file, io.IOBase):
            try:
                with open(file, "rb") as stream:
                    raw = stream.read()
            except OSError:
                return original(file, *args, **kwargs)
            canonical = _canonical_bytes(raw)
            name = os.fspath(file)
            if isinstance(name, str):
                kwargs.setdefault("report_filename", name)
            result = original(io.BytesIO(canonical), *args, **kwargs)
            if b"include" in raw and not raw.endswith(canonical):
                _restore_include_paths(raw, result[2])
            return result
        return original(file, *args, **kwargs)

    parse_file.__bea_bom_wrapped__ = True  # type: ignore[attr-defined]
    beancount_parser.parse_file = parse_file
    _install_lexer()


def _install_lexer() -> None:
    """Give `lexer.lex_iter` the same reading, for `doctor lex`.

    The token dump is the one diagnostic that never reaches `parse_file`, so
    it alone reported the mark as an error token glued to the first keyword
    while every other command read the file cleanly (w5/135).
    """
    from beancount.parser import lexer

    original: Any = lexer.lex_iter

    def lex_iter(file: Any, *args: Any, **kwargs: Any) -> Any:
        if not isinstance(file, io.IOBase):
            try:
                with open(file, "rb") as stream:
                    file = io.BytesIO(_canonical_bytes(stream.read()))
            except OSError:
                pass
        return original(file, *args, **kwargs)

    lexer.lex_iter = lex_iter


def _restore_include_paths(raw: bytes, options: dict[str, Any]) -> None:
    """Put each parsed include target back in the spelling the file has it in.

    Normalization is for the names a ledger declares; an include target names
    a file, and the loader opens and reports it under exactly that string.
    Read as NFC, a path with a decomposed component came back respelled: the
    include lines `bea` stages with absolute paths then reported every
    included file under a name no map-back table held, so a write took an
    error already in the books for a new one and quoted the staged copy
    (w5/144), and a normalization-sensitive volume could not open it at all.
    """
    from bea_engine.ledger.text import iter_includes

    written = [span.target for span in iter_includes(raw)]
    restored = []
    for target in options.get("include") or ():
        same = next((name for name in written if unicodedata.normalize("NFC", name) == target), None)
        if same is not None:
            written.remove(same)
        restored.append(target if same is None else same)
    options["include"] = restored


def _canonical_bytes(raw: bytes) -> bytes:
    """Ledger bytes with the BOM stripped and the text NFC-normalized.

    Editors on different platforms emit different normalizations of identical
    text; without this, Beancount reads NFC and NFD account names as two
    accounts and reports a false unknown-account error. Normalizing before
    the text reaches the parser merges them into one, while the file on disk
    keeps whatever bytes the editor wrote. Amounts, dates, and metadata keys
    are ASCII and pass through byte-identical; bytes that are not UTF-8 at
    all ride a surrogate round-trip back out unchanged.
    """
    if raw.startswith(UTF8_BOM):
        # The mark would survive normalization as U+FEFF and glue itself to
        # the first keyword again, so it is stripped as bytes first.
        raw = raw[len(UTF8_BOM) :]
    text = raw.decode("utf-8", errors="surrogateescape")
    return unicodedata.normalize("NFC", text).encode("utf-8", errors="surrogateescape")
