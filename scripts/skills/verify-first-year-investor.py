#!/usr/bin/env python3
"""Read-only checks for the synthetic first-year investor journey.

Examples (keep snapshots and agent logs outside the workspace):
  python3 verify-first-year-investor.py snapshot --workspace /tmp/books --output /tmp/before.json
  python3 verify-first-year-investor.py verify --workspace /tmp/books --checkpoint year_end
  python3 verify-first-year-investor.py verify --workspace /tmp/books --checkpoint closed_june --before /tmp/before.json

Requires an independent Git repository and bea on PATH (or --bea /path/to/bea).
Checkpoint figures come from docs/skills/examples/first-year-investor/expectations.json
and are compared against live `bea` queries, never against the guide's prose.
Only .git internals are excluded from file snapshots; HEAD and index are recorded
separately. Verification itself must leave workspace, HEAD, and index unchanged.
The fixture is single-file; include directives are rejected.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

EXPECTATIONS = Path(__file__).resolve().parents[2] / 'docs/skills/examples/first-year-investor/expectations.json'


class VerificationError(Exception):
    """An observation was unavailable or did not match the scenario."""


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def run(args, workspace):
    result = subprocess.run(args, cwd=workspace, env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'},
                            capture_output=True, check=False, timeout=90)
    require(result.returncode == 0,
            f"Command failed ({result.returncode}): {' '.join(map(str, args))}\n"
            + result.stderr.decode(errors='replace').strip())
    return result.stdout


def git(workspace, *args):
    return run(['git', '-C', str(workspace), *args], workspace)


def file_identity(path):
    info = path.lstat()
    mode = stat.S_IMODE(info.st_mode)
    if stat.S_ISLNK(info.st_mode):
        return {'type': 'symlink', 'target': os.readlink(path), 'mode': mode}
    require(stat.S_ISREG(info.st_mode), f'Unsupported file type: {path}')
    return {'type': 'file', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'mode': mode}


def capture(workspace, ledger):
    root = Path(git(workspace, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    require(root == workspace, 'Workspace must be its own Git repository root, not a parent repository subdirectory.')
    files = {}

    def visit(directory):
        for path in sorted(directory.iterdir()):
            if path == workspace / '.git':
                continue
            if path.is_symlink() or not path.is_dir():
                files[path.relative_to(workspace).as_posix()] = file_identity(path)
            else:
                visit(path)

    visit(workspace)
    head = git(workspace, 'rev-parse', '--verify', 'HEAD').decode().strip()
    index = Path(git(workspace, 'rev-parse', '--git-path', 'index').decode().strip())
    if not index.is_absolute():
        index = workspace / index
    require(not index.is_symlink(), 'Git index must not be a symlink.')
    try:
        index_id = file_identity(index)
    except FileNotFoundError:
        index_id = None
    return {'schema_version': 1, 'workspace': str(workspace), 'ledger': ledger,
            'files': files, 'head': head, 'index': index_id}


def unchanged(before, after, *, git_state=True):
    require(before['workspace'] == after['workspace'] and before['ledger'] == after['ledger'],
            'Snapshot belongs to a different workspace or ledger.')
    require(before['files'] == after['files'], 'Workspace files changed (contents, modes, paths, or symlink targets).')
    if git_state:
        require(before['head'] == after['head'], 'Git HEAD changed.')
        require(before['index'] == after['index'], 'Git index changed.')


def outside_workspace(path, workspace):
    resolved = path.resolve()
    require(not resolved.is_relative_to(workspace), 'Snapshot path must be outside the inspected workspace.')
    return resolved


def read_snapshot(path, workspace, ledger):
    data = json.loads(outside_workspace(path, workspace).read_text())
    require(isinstance(data, dict) and data.get('schema_version') == 1, 'Unsupported snapshot format.')
    require(all(key in data for key in ('workspace', 'ledger', 'files', 'head', 'index')),
            'Incomplete snapshot.')
    require(data['workspace'] == str(workspace) and data['ledger'] == ledger,
            'Snapshot belongs to a different workspace or ledger.')
    return data


def bea_read(bea, workspace, ledger, *args):
    value = json.loads(run([bea, '--file', str(workspace / ledger), '--json', '--no-input', *args], workspace))
    require(isinstance(value, dict) and 'data' in value, f'Invalid bea envelope for {args[0]}.')
    require(not value.get('error') and not value.get('errors'), f'bea returned errors for {args[0]}.')
    require(value.get('truncated') is False, f'bea response is truncated or lacks a completeness indicator: {args[0]}.')
    return value['data']


def number(value):
    require(isinstance(value, str), f'Expected a decimal string, got {value!r}.')
    result = Decimal(value)
    require(result.is_finite(), 'Non-finite amount.')
    return result


class Ledger:
    def __init__(self, bea, workspace, ledger):
        self.bea, self.workspace, self.ledger = bea, workspace, ledger

    def query(self, sql):
        data = bea_read(self.bea, self.workspace, self.ledger, 'query', sql)
        require(isinstance(data, dict) and isinstance(data.get('rows'), list), f'Expected query rows for: {sql}')
        return data['rows']

    def usd_balance(self, account):
        rows = self.query(f"SELECT sum(number) WHERE account = '{account}' AND currency = 'USD'")
        return number(rows[0][0]) if rows and rows[0][0] is not None else Decimal('0')

    def lots(self, account, commodity):
        rows = self.query(
            f"SELECT cost_number, cost_date, sum(number) AS units WHERE account = '{account}' "
            f"AND currency = '{commodity}' GROUP BY cost_number, cost_date ORDER BY cost_date")
        return [(number(r[0]), r[1], number(r[2])) for r in rows if number(r[2]) != 0]

    def scalar(self, sql):
        rows = self.query(sql)
        require(len(rows) == 1 and len(rows[0]) == 1 and rows[0][0] is not None, f'Expected one figure for: {sql}')
        return number(rows[0][0])


def want(value):
    return number(value)


def expect(actual, wanted, label):
    require(actual == wanted, f'{label}: got {actual}, expected {wanted}.')


def verify_checkpoint(led, name, cp):
    if name == 'initialized':
        expect(led.usd_balance('Assets:Checking'), want(cp['checking_usd']), 'checking')
    elif name == 'seeded':
        expect(led.usd_balance('Assets:Brokerage'), want(cp['brokerage_cash_usd']), 'brokerage cash')
        wanted = [(want(a), b, want(c)) for a, b, c in cp['vti_lots']]
        require(led.lots('Assets:Brokerage', 'VTI') == wanted, 'Seeded VTI lots differ.')
        wanted = [(want(a), b, want(c)) for a, b, c in cp['btc_lots']]
        require(led.lots('Assets:Crypto:Wallet', 'BTC') == wanted, 'Seeded BTC lots differ.')
    elif name == 'purchased':
        expect(led.usd_balance('Assets:Checking'), want(cp['checking_usd']), 'checking')
        expect(led.usd_balance('Liabilities:Mortgage:OakSt'), want(cp['mortgage_usd']), 'mortgage')
        expect(led.usd_balance('Assets:Escrow:OakSt'), want(cp['escrow_usd']), 'escrow')
        lots = led.lots('Assets:Property:OakSt', 'OAKST')
        require(len(lots) == 1 and lots[0][0] * lots[0][2] == want(cp['property_basis_usd']), 'Property basis differs.')
    elif name == 'imported':
        expect(led.usd_balance('Assets:Brokerage'), want(cp['brokerage_cash_usd']), 'brokerage cash')
        expect(led.scalar("SELECT -sum(number) WHERE account = 'Income:CapitalGains'"),
               want(cp['booked_gains_usd']), 'booked gains')
        wanted = [(want(a), b, want(c)) for a, b, c in cp['vti_lots_left']]
        require(led.lots('Assets:Brokerage', 'VTI') == wanted, 'VTI lots after import differ.')
    elif name == 'paid':
        expect(led.usd_balance('Assets:Checking'), want(cp['checking_usd']), 'checking')
        expect(led.usd_balance('Liabilities:Mortgage:OakSt'), want(cp['mortgage_usd']), 'mortgage')
        expect(led.usd_balance('Assets:Escrow:OakSt'), want(cp['escrow_usd']), 'escrow')
        expect(led.usd_balance('Expenses:Interest'), want(cp['interest_total_usd']), 'interest total')
    elif name == 'swapped':
        expect(led.scalar("SELECT -sum(number) WHERE account = 'Income:CapitalGains'"),
               want(cp['booked_gains_2026_usd']), 'booked gains')
        btc = led.lots('Assets:Crypto:Wallet', 'BTC')
        require(sum(u for _, _, u in btc) == want(cp['btc_units_left']), 'BTC units after swap differ.')
        eth = led.lots('Assets:Crypto:Wallet', 'ETH')
        require(eth == [(want(cp['eth_lot'][0]), cp['eth_lot'][1], want(cp['eth_lot'][2]))], 'ETH lot differs.')
    elif name == 'year_end':
        rows = led.query(
            "SELECT currency AS commodity, sum(number * cost_number) AS cost, "
            "sum(number(value(position))) AS market, "
            "sum(number(value(position))) - sum(number * cost_number) AS unrealized "
            "WHERE cost_number IS NOT NULL AND currency(value(position)) = cost_currency "
            "GROUP BY commodity ORDER BY commodity")
        seen = {r[0] for r in rows}
        require(seen == set(cp['holdings_market_usd']), f'Priced holdings differ: {sorted(seen)!r}.')
        for commodity, _cost, market, unrealized in rows:
            expect(number(market), want(cp['holdings_market_usd'][commodity]), f'{commodity} market')
            expect(number(unrealized), want(cp['unrealized_usd'][commodity]), f'{commodity} unrealized')
        expect(led.scalar("SELECT -sum(number) AS booked WHERE account ~ 'CapitalGains' "
                          "AND currency = 'USD' AND date >= 2026-01-01 AND date < 2027-01-01"),
               want(cp['realized_2026_booked_usd']), 'realized 2026 booked')
        expect(led.usd_balance('Assets:Checking'), want(cp['checking_usd']), 'checking')
    elif name == 'closed_june':
        # Ledger figures are the 'paid' checkpoint's (main runs it first);
        # here only the day-after checking assertion is new.
        pass
        balances = bea_read(led.bea, led.workspace, led.ledger, 'list', 'balance', '--limit', '100')
        found = [(b['date'], b['account'], number(b['amount']['number']))
                 for b in balances if b['account'] == 'Assets:Checking']
        require(found == [('2026-07-01', 'Assets:Checking', Decimal('25400.00'))],
                f'Checking assertion differs: {found!r}.')
    else:
        raise VerificationError(f'Unknown checkpoint: {name}.')


def verify_close(workspace, ledger, before, current):
    unchanged(before, current, git_state=False)
    parents = git(workspace, 'rev-list', '--parents', '-n', '1', 'HEAD').decode().split()
    require(parents == [current['head'], before['head']], 'Close must add exactly one non-merge commit to the recorded HEAD.')
    changed = git(workspace, 'diff-tree', '--no-commit-id', '--name-only', '-r', '-z', 'HEAD').decode().split('\0')
    changed = sorted(p for p in changed if p)
    require(changed == [ledger], f'Close committed unexpected paths: {changed!r}.')
    require(git(workspace, 'show', f'HEAD:{ledger}') == (workspace / ledger).read_bytes(),
            'Working ledger differs from the committed ledger.')
    subject = git(workspace, 'show', '-s', '--format=%s', 'HEAD').decode().strip()
    require(re.fullmatch(r'close: 2026-06 — 1 tied, [1-9]\d* not tied', subject),
            f'Close subject must report June with exactly the one tied account; got: {subject!r}.')


def resolve_workspace(workspace, ledger):
    workspace = workspace.resolve(strict=True)
    ledger_path = workspace / ledger
    require(not Path(ledger).is_absolute() and '..' not in Path(ledger).parts,
            'Ledger must be a relative path inside the workspace.')
    require(ledger_path.resolve(strict=True).is_relative_to(workspace) and not ledger_path.is_symlink(),
            'Ledger must be a regular workspace file, not an external path or symlink.')
    return workspace


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    snap = commands.add_parser('snapshot', help='Record workspace, HEAD, and index outside the workspace.')
    verify = commands.add_parser('verify', help='Compare a checkpoint with the independent fixture expectations.')
    for command in (snap, verify):
        command.add_argument('--workspace', required=True, type=Path)
        command.add_argument('--ledger', default='main.bean')
    snap.add_argument('--output', required=True, type=Path)
    verify.add_argument('--checkpoint', required=True)
    verify.add_argument('--before', type=Path)
    verify.add_argument('--bea', default='bea')
    args = parser.parse_args(argv)
    try:
        workspace = resolve_workspace(args.workspace, args.ledger)
        current = capture(workspace, args.ledger)
        if args.command == 'snapshot':
            output = outside_workspace(args.output, workspace)
            with output.open('x') as stream:
                json.dump(current, stream, indent=2)
                stream.write('\n')
            unchanged(current, capture(workspace, args.ledger))
            print(f'PASS snapshot: {output}')
            return 0
        expected = json.loads(EXPECTATIONS.read_text())
        name = args.checkpoint
        require(name in expected['checkpoints'], f'Unknown checkpoint: {name}.')
        require(name != 'closed_june' or args.before is not None,
                'closed_june requires --before from immediately before the close commit.')
        before = read_snapshot(args.before, workspace, args.ledger) if args.before else None
        try:
            require(not re.search(r'^\s*include\s+', (workspace / args.ledger).read_text(), re.MULTILINE),
                    'This single-file fixture does not support include directives.')
            result = bea_read(args.bea, workspace, args.ledger, 'check')
            require(isinstance(result, dict) and result.get('valid') is True and result.get('errors') == [],
                    'bea check did not return a passing error list.')
            led = Ledger(args.bea, workspace, args.ledger)
            if name == 'closed_june':
                verify_checkpoint(led, 'paid', expected['checkpoints']['paid'])
            verify_checkpoint(led, name, expected['checkpoints'][name])
            if name == 'closed_june':
                verify_close(workspace, args.ledger, before, current)
        finally:
            unchanged(current, capture(workspace, args.ledger))
        print(f'PASS {name}: expected ledger state; verification preserved workspace, HEAD, and index.')
        return 0
    except (VerificationError, OSError, ValueError, KeyError, TypeError, InvalidOperation, subprocess.TimeoutExpired) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
