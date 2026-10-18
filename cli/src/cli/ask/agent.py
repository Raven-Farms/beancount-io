from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from pydantic_ai import Agent, AgentRunResult, ModelRetry, RunContext
from pydantic_ai.exceptions import AgentRunError, ModelAPIError, ModelHTTPError, UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import UsageLimits

from cli import output
from cli.ask.results import format_result
from cli.ask.skills import AgentSkill, build_skills_index_prompt
from cli.engine import launch
from cli.errors import BeaError, LedgerError, error_from_status, redirect_error, request_id_from
from cli.errors import server_message as _server_message

_SYSTEM_PROMPT = """You are a helpful Beancount accounting assistant.
Use the run_bql_query tool to retrieve data from the user's ledger, then answer their question.
Use the write_directive tool to append beancount directives to the ledger file when the user asks to add entries.

BQL (Beancount Query Language) is SQL-like but NOT standard SQL. Key rules:

The default table is postings — one row per posting, so a transaction with two
postings is two rows. `FROM #entries` selects whole entries instead (one row per
directive, with a `type` column); `#postings`, `accounts`, `balances` and
`prices` are the other relations. Counting the default table counts postings.
Columns: date, account, number, currency, position, payee, narration, tags, flag.
Use SELECT DISTINCT to deduplicate (e.g. one row per account or per transaction).
`count(DISTINCT x)` is not valid in this dialect — count a subquery instead.
tags and links hold a whole set per entry, so DISTINCT and GROUP BY cannot take
them. Wrap them first: joinstr(tags) is a string and behaves like any other
column, and 'grocery' IN tags tests one tag. Do not rely on the order of tags
inside a joinstr result.

Common examples:
  List all open accounts:
    SELECT DISTINCT account WHERE close_date(account) IS NULL ORDER BY account
  List accounts with their open date:
    SELECT DISTINCT account, open_date(account) WHERE close_date(account) IS NULL ORDER BY account
  Current balances by account:
    SELECT account, sum(position) GROUP BY account
  Filter by account type:
    SELECT account, sum(position) WHERE account ~ '^Expenses' GROUP BY account
  Transactions in a date range:
    SELECT date, payee, narration WHERE date >= 2024-01-01 AND date < 2025-01-01
  Distinct currencies used:
    SELECT DISTINCT currency
  Distinct tag combinations:
    SELECT DISTINCT joinstr(tags)
  Entries carrying one tag:
    SELECT date, narration WHERE 'grocery' IN tags
  How many transactions there are (count entries, not postings):
    SELECT count(*) FROM #entries WHERE type = 'transaction'
    -- bare `SELECT count(*)` answers a different question: it counts postings.
  Largest / top N — "largest" means ORDER BY ... DESC:
    SELECT date, payee, narration, number WHERE account ~ '^Expenses' ORDER BY number DESC LIMIT 1
    -- ascending order would report the smallest; say DESC when asked for the biggest.
  Net worth, or any balance as of a date (filter by account type, never the whole ledger):
    SELECT sum(position) FROM CLOSE ON 2024-03-01 WHERE account ~ '^(Assets|Liabilities)'
    SELECT account, sum(position) WHERE account ~ '^(Assets|Liabilities)' AND date <= 2024-03-01 GROUP BY account
  Holdings in one currency (filter by account, because the currency's legs net to zero ledger-wide):
    SELECT account, sum(position) WHERE currency = 'EUR' AND account ~ '^(Assets|Liabilities)' GROUP BY account

Every transaction balances, so an unfiltered sum(position) — over the whole
ledger, or filtered only by date or by currency — is zero by construction. A
result of 0 means the matched postings cancelled out, not that the ledger is
empty: re-run it restricted to the accounts the question is about before
concluding anything. Each result tells you how many rows it has; "0 row(s)"
means nothing matched, and a cell reading 0 is a real zero.

Other functions: year(date), month(date), root(account), leaf(account), units(position), cost(position)
FROM also takes temporal modifiers instead of a relation: FROM OPEN ON <date> /
FROM CLOSE [ON <date>] / FROM CLEAR. Use the run_bql_query tool for SELECT
(and BALANCES / JOURNAL); it does not run PRINT or dot commands.

Prefer aggregates to enumeration: a result is truncated past a few hundred rows,
and a total, a GROUP BY or a date range answers most questions. When a result
says it was truncated, say so in your answer.

If a query fails, read the error carefully, fix the syntax, and retry.

Beancount directive syntax for write_directive:
  Transaction:
    2024-01-15 * "Payee" "Narration"
      Account:One   100.00 USD
      Account:Two  -100.00 USD
  Open account:    2024-01-01 open Assets:Cash USD
  Close account:   2024-12-31 close Assets:Cash
  Balance assert:  2024-01-31 balance Assets:Cash 500.00 USD
  Note:            2024-01-15 note Assets:Cash "some note"
  Price:           2024-01-15 price AAPL 185.00 USD
Always use correct indentation (two spaces for postings). Use today's date if not specified."""


#: What one question may spend. `ask` is the only command that costs money per
#: call, so the ceiling is the CLI's own choice rather than the AI SDK's default
#: of 50 requests: a ledger question needs a handful of queries, and a model that
#: keeps calling tools without answering is looping, not working. Every request
#: carries the whole growing history, so the tail of a loop is also the expensive
#: part. Tripping this is reported in the CLI's own words by `translated_failures`.
REQUEST_LIMIT = 12
TOOL_CALLS_LIMIT = 10

#: What one answer may be long enough to say. A request that names no output cap
#: reserves the model's whole default allowance, and the hosted proxy budgets
#: against what a request reserves: at the edge of an account's window the
#: uncapped request is the first one refused, while a modestly capped one still
#: fits (w3/446). An answer here is prose about a ledger — a few paragraphs, or a
#: short table — so this is generous for the job and small against a window.
MAX_OUTPUT_TOKENS = 1500


#: Said when an answer stopped at `MAX_OUTPUT_TOKENS`: its text ends wherever
#: the cap fell, mid-figure included, and printed as if complete (w5/546).
CUT_OFF_NOTICE = "The answer reached the per-answer limit and was cut off; ask a narrower question."


def cut_off(result: AgentRunResult[str]) -> bool:
    """Whether a run's final answer stopped at the output cap instead of finishing."""
    for message in reversed(result.all_messages()):
        if isinstance(message, ModelResponse):
            return getattr(message, "finish_reason", None) == "length"
    return False


def usage_limits() -> UsageLimits:
    """The per-question budget, built the same way for the REPL and for `--print`."""
    return UsageLimits(request_limit=REQUEST_LIMIT, tool_calls_limit=TOOL_CALLS_LIMIT)


def model_settings() -> ModelSettings:
    """The request settings every `ask` call carries, chiefly the output cap."""
    return ModelSettings(max_tokens=MAX_OUTPUT_TOKENS)


@dataclass
class WritePermission:
    approve_all: bool = False
    deny_all: bool = False
    #: Called with the directive text and the append destination the engine's
    #: dry run resolved — never the root ledger, which `--into` makes wrong.
    confirm_fn: Callable[[str, str, list[str]], str] | None = None


@dataclass
class BqlDeps:
    file: Path
    write_permission: WritePermission = field(default_factory=WritePermission)
    skills: dict[str, AgentSkill] = field(default_factory=dict)
    into: Path | None = None
    #: What this question has written: one (directive count, file) per approved
    #: write that landed. A failure report must not deny a write that happened —
    #: told "nothing was written", a user retries and duplicates the entry
    #: (w1/095). `translated_failures` resets it at the start of every turn.
    writes: list[tuple[int, str]] = field(default_factory=list)


def written_so_far(deps: BqlDeps | None) -> str:
    """What this question wrote, as the clause a failure report ends with."""
    if deps is None or not deps.writes:
        return "nothing was written to your ledger"
    per_file: dict[str, int] = {}
    for count, target in deps.writes:
        per_file[target] = per_file.get(target, 0) + count
    landed = ", ".join(f"{count} directive(s) to {target}" for target, count in per_file.items())
    return f"this question had already written {landed}, which stay in your ledger"


@contextmanager
def translated_failures(deps: BqlDeps | None = None) -> Iterator[None]:
    """Report the proxy's HTTP failures the way every other command reports them.

    `ask` reaches the service over the OpenAI protocol through the AI SDK
    rather than through `cli.api.client`, so it never met the status table in
    `error_from_status` that the exit table is written against. A rejected
    credential — expired, revoked, wrong environment — therefore exited 1 with
    the SDK's own `status_code: …, model_name: …, body: …` string: a script
    branching on exit 3 to re-login never fired, and the user read the proxy's
    internal model name instead of a remedy.

    Routing through that same table is what keeps `ask` and `cloud` from
    drifting: 401/403 become `AuthError` with the BEA_TOKEN-aware remedy, and
    rate limits and 5xx get their documented sentences too.

    The AI SDK's own run failures are translated here for the same reason. Left
    alone they fell past this context manager into the catch-all in `main.py`,
    which printed them verbatim: the user read a third-party limit name
    (`request_limit`), a knob `bea` does not expose (the tool retry count), and a
    link to another project's documentation. Every arm below says what happened,
    what was written, and what to try instead — and none of them quotes
    the SDK's sentence, because that sentence is the defect.

    `deps` is the turn's state: its record of writes is cleared on entry, so
    every arm can say what this question actually wrote — "nothing" only when
    that is true — instead of a claim written for `--print`, where writes are
    impossible (w1/095).
    """
    if deps is not None:
        deps.writes.clear()
    try:
        yield
    except ModelHTTPError as exc:
        if 300 <= exc.status_code < 400:
            raise _naming_writes(redirect_error(exc.status_code, getattr(exc, "headers", None)), deps) from exc
        quota = _quota_refusal(exc.body, written_so_far(deps))
        if quota is not None:
            raise BeaError(quota) from exc
        raise _naming_writes(error_from_status(exc.status_code, _server_message(exc.body)), deps) from exc
    except ModelAPIError as exc:
        # The SDK wraps redirects as ModelAPIError rather than ModelHTTPError,
        # just like connection failures. Inspect the actual cause before
        # claiming that the server could not be reached.
        raise _naming_writes(_model_api_error(exc), deps) from exc
    except UnreadableModelReply as exc:
        # The sentence every other unreadable success gets (USAGE.md), with
        # what this question wrote, never the parser's own words.
        raise BeaError(
            f"Unexpected server response (HTTP {exc.status}) from the assistant; {written_so_far(deps)}. "
            "Retry the question, or run the query yourself with 'bea query'."
        ) from exc
    except UsageLimitExceeded as exc:
        raise BeaError(
            f"The assistant kept querying without reaching an answer and stopped at this question's "
            f"budget ({REQUEST_LIMIT} model requests, {TOOL_CALLS_LIMIT} ledger queries); "
            f"{written_so_far(deps)}. "
            "Ask a narrower question, or run the query yourself with 'bea query'."
        ) from exc
    except AgentRunError as exc:
        raise BeaError(
            f"The assistant could not complete this question ({type(exc).__name__}); "
            f"{written_so_far(deps)}. Rephrase the question and retry, "
            "or run the query yourself with 'bea query'."
        ) from exc


def _naming_writes(error: BeaError, deps: BqlDeps | None) -> BeaError:
    """The status table's sentence, plus the write it would otherwise leave out.

    Those sentences make no claim about the ledger, so nothing is added when the
    question wrote nothing; after a write, silence reads as "nothing happened"
    and invites the retry that duplicates the entry.
    """
    if deps is not None and deps.writes:
        clause = written_so_far(deps)
        error.args = (f"{error} Note: {clause[0].upper()}{clause[1:]}.",)
    return error


def _model_api_error(exc: BaseException) -> BeaError:
    """The CLI's HTTP or network sentence, built from whatever the SDK wrapped.

    A real HTTP response takes precedence over the connection fallback. Its
    SDK exception string can carry request details, so use only the response's
    status, headers and safely decoded server sentence. Transport failures keep
    the same translation as cloud commands.
    """
    import httpx

    from cli.errors import to_bea_error

    cause: BaseException | None = exc
    seen: set[int] = set()
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        response = getattr(cause, "response", None)
        if isinstance(response, httpx.Response):
            if 300 <= response.status_code < 400:
                return redirect_error(response.status_code, response.headers)
            body = getattr(cause, "body", None)
            if body is None:
                try:
                    body = response.json()
                except (ValueError, RecursionError):
                    pass
            return error_from_status(
                response.status_code, _server_message(body), request_id=request_id_from(response.headers)
            )
        if isinstance(cause, httpx.TransportError):
            return to_bea_error(cause)
        cause = cause.__cause__ or cause.__context__
    return BeaError(f"Could not reach the server ({type(exc).__name__}).")


def _quota_refusal(body: object, written: str = "nothing was written to your ledger") -> str | None:
    """The account's AI budget, refused: which quota, and when it comes back.

    The proxy answers a quota rejection with its own code and, when it knows it,
    the moment the window reopens. Both are worth more to the reader than the
    status line, and the code survives however deeply the envelope nests it —
    which is why this looks at the whole body rather than at one key.
    """
    text = body if isinstance(body, str) else json.dumps(body, default=str)
    if "QUOTA_EXCEEDED" not in text:
        return None
    # The escape-tolerant form on purpose: the code and the reset time may sit
    # inside a JSON document that is itself the value of a JSON string, so the
    # quotes around them may be escaped once (w3/445 is the same envelope).
    until = re.search(r'blockedUntil\\?"\s*:\s*\\?"([^"\\]+)', text)
    when = f" It resets at {until.group(1)}." if until else ""
    return (
        "This account's hosted AI quota is used up, so the question was refused; "
        f"{written}.{when} "
        "Run the query yourself with 'bea query' in the meantime."
    )


_ROOT_OPTION = re.compile(r'^option[ \t]+"name_(assets|liabilities|equity|income|expenses)"[ \t]+"([^"\\\n]+)"', re.M)
_DEFAULT_ROOTS = {"assets": "Assets", "liabilities": "Liabilities", "equity": "Equity", "income": "Income"}
_DEFAULT_ROOTS["expenses"] = "Expenses"


def ledger_root_names(file: Path) -> dict[str, str]:
    """The account roots this ledger renames, default name to its own, from the root file's options.

    The prompt's recipes filter on `^Expenses` and `^(Assets|Liabilities)`, so
    on a ledger with `option "name_expenses" "Aufwand"` a model following them
    queried roots that hold nothing and read the 0 rows as no data (w5/403).
    Read as text: the frontend never loads the ledger, and Beancount takes
    these options from the root file, the last one winning.
    """
    try:
        text = file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    named = {_DEFAULT_ROOTS[key]: name for key, name in _ROOT_OPTION.findall(text)}
    return {default: name for default, name in named.items() if name != default}


def roots_prompt(renamed: dict[str, str]) -> str:
    """The system-prompt line naming this ledger's account roots, or nothing for the defaults."""
    if not renamed:
        return ""
    pairs = ", ".join(f"{name} (for {default})" for default, name in renamed.items())
    default, name = next(iter(renamed.items()))
    return (
        f"This ledger renames its account roots: {pairs}. Use those names wherever the examples above say "
        f"{', '.join(renamed)}, as in account ~ '^{name}' rather than '^{default}'."
    )


class UnreadableModelReply(Exception):
    """A successful model response whose body the SDK could not read (w5/373)."""

    def __init__(self, status: int) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status


class _ProxyChatModel(OpenAIChatModel):
    """The chat model, with a reply its SDK cannot read raised as one exception.

    An empty `choices` array (what some OpenAI-compatible gateways send for a
    filtered prompt) is an `IndexError` in the SDK's response handling, and an
    empty, HTML or truncated JSON body a `JSONDecodeError` in its parser. Both
    reached the catch-all in `main.py` and printed `list index out of range`.
    A body cut inside a UTF-8 character or sent in another charset is a
    `UnicodeDecodeError`, one nested past the parser's depth a `RecursionError`,
    and a `"type": "custom"` tool call the SDK's own `RuntimeError` (w5/547).
    Only the model call is wrapped, so a fault in bea's own tools is never
    reported as the server's.
    """

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        from openai import APIResponseValidationError

        try:
            return await super().request(messages, model_settings, model_request_parameters)
        except APIResponseValidationError as exc:
            raise UnreadableModelReply(exc.response.status_code) from exc
        except (ValueError, IndexError, KeyError, TypeError, RecursionError) as exc:
            # The SDK parses only a successful body; any other status raises its
            # status error, which arrives as `ModelHTTPError`. `ValueError`
            # covers `JSONDecodeError` and `UnicodeDecodeError`.
            raise UnreadableModelReply(200) from exc
        except RuntimeError as exc:
            # Only the SDK's refusal of a custom tool call: its own run failures
            # (`AgentRunError`) are `RuntimeError`s too, and are reported apart.
            if type(exc) is not RuntimeError or not str(exc).startswith("Custom tool calls"):
                raise
            raise UnreadableModelReply(200) from exc


def make_agent(
    model_name: str,
    base_url: str,
    api_key: str,
    skills: list[AgentSkill] | None = None,
) -> Agent[BqlDeps, str]:
    model = _ProxyChatModel(
        model_name,
        provider=OpenAIProvider(base_url=base_url, api_key=api_key),
    )
    system_prompt = _SYSTEM_PROMPT
    if skills:
        system_prompt = system_prompt + build_skills_index_prompt(skills)
    agent: Agent[BqlDeps, str] = Agent(
        model,
        deps_type=BqlDeps,
        system_prompt=system_prompt,
        model_settings=model_settings(),
    )

    @agent.system_prompt
    def todays_date() -> str:
        return f"Today's date is {date.today().isoformat()}."

    @agent.system_prompt
    def account_roots(ctx: RunContext[BqlDeps]) -> str:
        return roots_prompt(ledger_root_names(ctx.deps.file))

    @agent.tool(retries=2)
    def run_bql_query(ctx: RunContext[BqlDeps], query: str) -> str:
        """Run a BQL SELECT (Beancount Query Language) against the user's Beancount ledger.

        Returns the matching rows with a row count. An invalid query or an invalid
        ledger comes back as an error to fix and retry.
        """
        if not query.strip():
            raise ModelRetry("The query is empty. Send a BQL SELECT statement.")
        try:
            # Rows and columns, not the rendered table: the row count, a visible
            # zero and a bounded result all need the typed shape (`ask.results`).
            data = launch.helper_json(["query", "--file", str(ctx.deps.file), query, "--format", "json"])
        except BeaError as exc:
            raise ModelRetry(_query_failure(exc)) from exc
        return format_result(query, data)

    # Models batch independent calls ("add a coffee and a lunch"), and
    # pydantic-ai runs a reply's sync tools at once in worker threads: two
    # consent selectors shared one terminal, an answer reached either panel,
    # and both dry runs predated either write (w5/544). One write at a time,
    # each dry run after the last write; a lock, not `sequential=True`, since
    # the ask extra accepts pydantic-ai releases older than that option.
    write_lock = threading.Lock()

    @agent.tool()
    def write_directive(ctx: RunContext[BqlDeps], directive: str) -> str:
        """Append Beancount directive text (one or more directives) to the ledger file.

        The text is validated first; invalid text is rejected with the reason and nothing
        is written. In an interactive session the user sees the directive and approves or
        declines it; in non-interactive mode writes are skipped. Returns one line: how many
        directives were added and to which file, or why nothing was written.
        """
        with write_lock:
            perm = ctx.deps.write_permission
            if perm.deny_all:
                return "Write denied (you denied all writes this session)."
            argv = ["append", "--file", str(ctx.deps.file), "--text", "-"]
            if ctx.deps.into is not None:
                argv += ["--into", str(ctx.deps.into)]
            try:
                preview = launch.helper_json([*argv, "--dry-run"], stdin=directive)
            except BeaError as exc:
                return _write_rejection(exc)
            if not perm.approve_all:
                if perm.confirm_fn is None:
                    return "Write skipped (non-interactive mode does not support writes)."
                # The dry run resolved where the text actually goes — with `--into`
                # that is an included file, not `deps.file`. The consent panel has to
                # name that file, so the preview's own answer is what it is built from.
                warnings = [str(warning) for warning in preview.get("warnings") or []]
                # The engine's aligned rendering is what lands in the file: the
                # proposal's tab indentation showed as `\x09` and was then written
                # as aligned spaces (w5/374).
                shown = preview.get("text")
                answer = perm.confirm_fn(
                    shown if isinstance(shown, str) else directive, str(preview["target"]), warnings
                )
                if answer == "a":
                    perm.approve_all = True
                elif answer == "d":
                    perm.deny_all = True
                    return "Write denied."
                elif answer == "n":
                    return "Write cancelled by user."
            try:
                result = launch.helper_json(
                    [*argv, "--token", json.dumps(preview["token"])],
                    stdin=directive,
                    writes=True,
                )
            except BeaError as exc:
                return _write_rejection(exc)
            ctx.deps.writes.append((int(result["written"]), str(result["target"])))
            return f"Added {result['written']} directive(s) to {result['target']}."

    @agent.tool()
    def get_skill_body(ctx: RunContext[BqlDeps], name: str) -> str:
        """Load the full instructions for an agent skill by name."""
        skill = ctx.deps.skills.get(name)
        if skill is None:
            available = ", ".join(ctx.deps.skills) or "none"
            return f"Skill '{name}' not found. Available skills: {available}."
        return skill.body or "(no body content)"

    return agent


def _query_failure(exc: BeaError) -> str:
    """What the BQL tool tells the model about a query that did not run (w5/549).

    The engine's details are what make a query fixable — the caret under the
    failing token, the columns the table has — so they travel with it, minus
    the lines that address a person at a shell (`bea query .tables`, `--debug`).
    A crash in the engine carries a traceback and is the engine's failure, not
    an invalid ledger: saying "Ledger is invalid" pushed the model to "fix" a
    ledger that loads.
    """
    message = str(exc).removesuffix(output.DEBUG_HINT).rstrip().rstrip(".")
    details = [line for line in exc.details if not line.lstrip().startswith("Run bea ")]
    if exc.traceback is not None:
        return (
            f"The query engine failed on this query ({message}); the ledger is not at fault. "
            "Rephrase the query and retry."
        )
    if isinstance(exc, LedgerError):
        return "Ledger is invalid: " + ("; ".join(details) or message)
    return "\n".join([f"BQL error: {message}.", *details, "Fix the query and retry."])


def _write_rejection(exc: BeaError) -> str:
    """Tool-facing write failure: keep the soft 'rejected' wording the model already sees."""
    message = str(exc)
    if message.startswith("Write rejected"):
        return message if not exc.details else message + " " + "; ".join(exc.details)
    return "Write rejected; nothing was written: " + message + (" " + "; ".join(exc.details) if exc.details else "")
