"""REFERENCE.md marks a pass-once list option as single and shows a paired flag's default by name (w5/527).

`add balance/price --amount` read "str (repeatable)" though a repeat exits 2,
and `cloud ledger create --private, --public` showed default "True" where
`--help` says `[default: private]`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _generator() -> Any:
    spec = importlib.util.spec_from_file_location("gen_reference", ROOT / "scripts" / "gen_reference.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _option(**fields: Any) -> SimpleNamespace:
    base = {
        "param_type_name": "option",
        "type": SimpleNamespace(name="text"),
        "multiple": False,
        "help": "",
        "required": False,
        "default": None,
        "opts": ["--x"],
        "secondary_opts": [],
        "is_bool_flag": False,
    }
    return SimpleNamespace(**(base | fields))


def test_a_pass_once_list_option_is_not_repeatable() -> None:
    gen = _generator()

    assert gen.type_label(_option(multiple=True, help="'NUMBER CURRENCY' (pass once)")) == "text"
    assert gen.type_label(_option(multiple=True, help="Tag (repeat)")) == "text (repeatable)"


def test_a_paired_flag_defaults_by_name() -> None:
    gen = _generator()

    paired = {"opts": ["--private"], "secondary_opts": ["--public"], "is_bool_flag": True}
    assert gen.default_label(_option(default=True, **paired)) == "private"
    assert gen.default_label(_option(default=False, **paired)) == "public"
    assert gen.default_label(_option(default=True, is_bool_flag=True)) == "True"


def test_the_generated_reference_reads_so() -> None:
    reference = (ROOT / "docs" / "REFERENCE.md").read_text()

    assert "| `--amount` | str | required | 'NUMBER [~ TOLERANCE] CURRENCY' (pass once) |" in reference
    assert "| `--amount` | str | required | 'NUMBER CURRENCY' (pass once) |" in reference
    assert "| `--private, --public` | flag | private | Ledger visibility |" in reference
    assert "str (repeatable) | required | 'NUMBER" not in reference
