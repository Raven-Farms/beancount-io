"""An unattended clone keeps the user's SSH command and only adds BatchMode (w5/370).

`_git_env` set `GIT_SSH_COMMAND` to `ssh -o BatchMode=yes` whenever it was
unset. Git ranks that above `core.sshCommand` and `GIT_SSH`, so a dedicated
key or an agent wrapper that clones interactively was dropped in exactly the
modes agents use (`--json`, `--no-input`, no TTY). The git server here is a
local bare repository behind a fake ssh wrapper.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from cli.commands.cloud.ledger.manager import _git_env, clone_ledger


@pytest.fixture
def git_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty global git config, so the user's real one never leaks in."""
    config = tmp_path / "gitconfig"
    config.write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for name in ("GIT_SSH_COMMAND", "GIT_SSH", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS", "GIT_TERMINAL_PROMPT"):
        monkeypatch.delenv(name, raising=False)
    return config


def _set_ssh_command(config: Path, command: str) -> None:
    subprocess.run(["git", "config", "--file", str(config), "core.sshCommand", command], check=True)


def test_no_ssh_configuration_gets_batch_mode_ssh(git_config: Path) -> None:
    env = _git_env(unattended=True)
    assert env["GIT_SSH_COMMAND"] == "ssh -o BatchMode=yes"
    assert env["GIT_TERMINAL_PROMPT"] == "0"


def test_an_attended_clone_leaves_the_environment_alone(git_config: Path) -> None:
    _set_ssh_command(git_config, "ssh -i ~/.ssh/beancount_key")
    assert "GIT_SSH_COMMAND" not in _git_env(unattended=False)


def test_git_ssh_command_is_kept_and_extended(git_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_SSH_COMMAND", "ssh -i /keys/env_key")
    _set_ssh_command(git_config, "ssh -i /keys/config_key")
    assert _git_env(unattended=True)["GIT_SSH_COMMAND"] == "ssh -i /keys/env_key -o BatchMode=yes"


def test_core_ssh_command_is_kept_and_extended(git_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_ssh_command(git_config, "ssh -i ~/.ssh/beancount_key")
    # core.sshCommand outranks GIT_SSH, as it does for git itself.
    monkeypatch.setenv("GIT_SSH", "/usr/local/bin/other-ssh")
    assert _git_env(unattended=True)["GIT_SSH_COMMAND"] == "ssh -i ~/.ssh/beancount_key -o BatchMode=yes"


def test_git_ssh_program_is_kept_and_extended(git_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_SSH", "/opt/agent tools/ssh-wrapper")
    assert _git_env(unattended=True)["GIT_SSH_COMMAND"] == "'/opt/agent tools/ssh-wrapper' -o BatchMode=yes"


def test_a_repository_config_where_bea_runs_is_not_read(
    git_config: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `git clone` does not read the enclosing repository's config, so neither does bea.
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "core.sshCommand", "ssh -i /keys/local"], check=True)
    monkeypatch.chdir(repo)
    assert _git_env(unattended=True)["GIT_SSH_COMMAND"] == "ssh -o BatchMode=yes"


def test_a_putty_family_program_is_not_given_openssh_options(git_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_SSH", "C:/Program Files/PuTTY/plink.exe")
    assert _git_env(unattended=True)["GIT_SSH_COMMAND"] == shlex.quote("C:/Program Files/PuTTY/plink.exe")


@pytest.mark.skipif(os.name != "posix", reason="the fake ssh wrapper is a POSIX shell script")
@pytest.mark.parametrize("setting", ["core.sshCommand", "GIT_SSH"])
def test_an_unattended_clone_runs_the_configured_wrapper(
    git_config: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, setting: str
) -> None:
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "init", "-q", str(seed)], check=True)
    (seed / "main.bean").write_text('option "operating_currency" "USD"\n')
    git = ["git", "-C", str(seed), "-c", "user.name=QA", "-c", "user.email=qa@example.invalid"]
    subprocess.run([*git, "add", "main.bean"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "seed"], check=True)
    subprocess.run([*git, "push", "-q", str(origin), "HEAD"], check=True)

    calls = tmp_path / "calls.log"
    wrapper = tmp_path / "fakessh"
    wrapper.write_text(
        "#!/bin/sh\n"
        f'echo "$*" >> {shlex.quote(str(calls))}\n'
        # git's variant probe (`-G`): answer like a non-OpenSSH program.
        'for arg in "$@"; do [ "$arg" = "-G" ] && exit 1; done\n'
        f"exec git-upload-pack {shlex.quote(str(origin))}\n"
    )
    wrapper.chmod(0o755)
    if setting == "GIT_SSH":
        monkeypatch.setenv("GIT_SSH", str(wrapper))
    else:
        _set_ssh_command(git_config, shlex.quote(str(wrapper)))

    target = tmp_path / "book"
    clone_ledger("git@127.0.0.1:qa/book.git", target, unattended=True)

    assert (target / "main.bean").is_file()
    used = calls.read_text().splitlines()
    assert used, "the configured ssh wrapper was never run"
    assert all("-o BatchMode=yes" in line for line in used)


def test_ssh_command_lookup_survives_a_missing_git(git_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(Path(sys.executable).parent / "no-such-dir"))
    assert _git_env(unattended=True)["GIT_SSH_COMMAND"] == "ssh -o BatchMode=yes"
