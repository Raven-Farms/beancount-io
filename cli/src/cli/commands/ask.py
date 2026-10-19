"""`bea ask` — the only command that needs an LLM, and the only one that pays for it.

Nothing here imports the ask package or its AI dependencies at module scope:
`main.py` imports this module on every invocation, including `--help`, and a
first `bea check` must not load an LLM client it will never use.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from cli import context, output
from cli.errors import BeaError, UsageError
from cli.utils import IntoPath

_MISSING_EXTRA = (
    "bea ask needs the optional AI dependencies and a Beancount.io login. "
    "For uv: uv tool install 'beancount-io[ask]'. For Homebrew, keep brew for the base CLI "
    "and run: uvx --from 'beancount-io[ask]' bea ask --help. "
    "Then run bea cloud login. Model calls use the hosted Beancount.io AI service."
)


def ask(
    question: Annotated[str | None, typer.Argument(help="Question to ask (omit for an interactive session)")] = None,
    print_mode: Annotated[
        bool, typer.Option("--print", "-p", help="Print mode: answer once and exit (non-interactive)")
    ] = False,
    into: Annotated[
        Path | None,
        typer.Option("--into", click_type=IntoPath(), help="Write to an included file, relative to the root ledger"),
    ] = None,
) -> None:
    """Ask about a local ledger via hosted AI.

    Requires both beancount-io[ask] and credentials from bea cloud login.
    With Homebrew, use uvx --from 'beancount-io[ask]' bea ask QUESTION --print.
    Interactive edits are confirmed, validated, and written atomically.
    """
    ctx = context.current()
    if ctx.offline:
        # The model calls go through the hosted proxy (w5/515).
        raise UsageError(
            "bea ask requires network access: its model calls go through the hosted proxy; remove --offline."
        )
    model = "gpt-4o"
    file = ctx.entry_file()
    if ctx.json_output:
        raise UsageError("bea ask has no JSON output. Use 'bea query' for machine-readable results.")

    question = question or ""
    if not question.strip():
        if print_mode or ctx.no_input:
            raise UsageError("A question is required without a terminal (or with --print).")
        question = ""
    if not (print_mode or ctx.no_input) and not ctx.stdout_is_a_terminal:
        # The session draws its prompt and its write-approval panel on stdout:
        # redirected, the person saw nothing while a keystroke still approved
        # the AI's write (w5/550).
        raise UsageError(
            "bea ask's interactive session draws on the terminal, and stdout is redirected, so its "
            "write-approval panel would not be seen. Ask one question with --print "
            "(bea ask QUESTION --print > FILE), or run the session without redirecting stdout."
        )

    # The missing extra is checked before the credential: without it the
    # command cannot run at all, and "log in first" would be misleading advice.
    try:
        from cli.ask.agent import BqlDeps, cut_off_notice, make_agent, translated_failures, usage_limits
    except ImportError as exc:
        raise UsageError(_MISSING_EXTRA) from exc

    from cli.auth.credentials import require_credentials

    creds = require_credentials()

    from httpx import InvalidURL

    from cli.ask.skills import load_skills, project_skills_notice
    from cli.config import settings

    skills = load_skills()
    for line in project_skills_notice(skills):
        output.note(line)
    try:
        agent = make_agent(
            model_name=model,
            base_url=f"{settings().api_url}/api-gateway/ai/openai/",
            api_key=creds.token,
            skills=skills,
        )
    except (ImportError, ValueError, InvalidURL) as exc:
        # Proxy configuration fails before a model request, as for cloud.
        from cli.errors import proxy_refusal

        refusal = proxy_refusal(exc)
        if refusal is None:
            raise
        raise refusal from None
    deps = BqlDeps(file=file, skills={s.name: s for s in skills}, into=into)

    if print_mode or ctx.no_input:
        from rich.console import Console

        from cli.ask.render import answer_markdown

        console = Console()
        with console.status("[dim]Thinking…[/dim]", spinner="dots"), translated_failures(deps):
            result = agent.run_sync(question, deps=deps, usage_limits=usage_limits())
        console.print(answer_markdown(result.output))
        notice = cut_off_notice(result)
        if notice is not None:
            # Part of an answer is not the answer: a nonzero exit says so (w5/546).
            raise BeaError(notice)
    else:
        from cli.ask.repl import print_welcome, run_repl

        print_welcome()
        run_repl(agent, deps, default_input=question)
