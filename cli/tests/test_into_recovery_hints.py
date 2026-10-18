"""Root-ledger advice follows the invoked file, not an included write destination."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_into_no_side_effects import _add_args, _make_ledger, _run, _tree


@pytest.mark.parametrize("json_output", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("invoked_leaf", [False, True], ids=["root-with-into", "leaf-as-file"])
@pytest.mark.parametrize("ambiguous", [False, True], ids=["unknown-account", "ambiguous-currency"])
def test_recovery_advice_names_only_a_missing_root_context(
    tmp_path: Path, json_output: bool, invoked_leaf: bool, ambiguous: bool
) -> None:
    root = _make_ledger(tmp_path, "parts/*.bean")
    leaf = root.parent / "parts" / "older.bean"
    args = _add_args("Assets:Nope", into="parts/older.bean")
    if ambiguous:
        with root.open("a") as stream:
            stream.write('option "operating_currency" "EUR"\n')
        args[args.index("Assets:Nope -12.34 USD")] = "Assets:Nope -12.34"
    if invoked_leaf:
        args = args[:-2]
    before = _tree(root.parent)

    result = _run(tmp_path, leaf if invoked_leaf else root, *args, json_output=json_output)

    assert result.returncode == (2 if ambiguous else 1), result.stderr
    if json_output:
        error = json.loads(result.stderr)["error"]
        message = error["message"] + "\n" + "\n".join(error.get("details", []))
    else:
        message = result.stderr
    if ambiguous:
        assert "Currency is ambiguous for Assets:Nope" in message
        assert "specify NUMBER CURRENCY" in message
    else:
        assert "unknown account 'Assets:Nope'" in message
        assert "add open --account Assets:Nope" in message
    # A leaf as `--file` already runs through the root that includes it, with
    # `--into` set to the leaf (w5/343): the recipe is applied, never printed.
    assert "Run against the root" not in message
    assert "<command> --into" not in message
    assert _tree(root.parent) == before
