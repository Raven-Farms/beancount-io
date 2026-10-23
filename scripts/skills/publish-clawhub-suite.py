#!/usr/bin/env python3
"""Preview or publish one versioned ClawHub suite with the pinned external CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preview", "publish"))
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.folder / "plugin.json").read_text())
    version = manifest["version"]
    owner = os.environ.get("CLAWHUB_OWNER", "puncsky")
    name = f"@{owner}/{manifest['name']}"
    command = ["clawhub", "--no-input", "package"]
    if args.mode == "publish":
        if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch" or os.environ.get("GITHUB_REF") != "refs/heads/main":
            raise ValueError("publication requires a manual dispatch from main")
        if os.environ.get("CLAWHUB_MIT0_APPROVED") != "true" or not os.environ.get("CLAWHUB_OWNER"):
            raise ValueError("publication requires recorded MIT-0 approval and a publisher")
        result = subprocess.run(
            [*command, "inspect", name, "--version", version, "--files", "--json"],
            text=True, capture_output=True, check=False,
        )
        if result.returncode == 0:
            existing = json.loads(result.stdout)["version"]
            if (existing.get("verification") or {}).get("scanStatus") in {"pending", "not-run", "malicious"}:
                raise ValueError("version is not a verified release; inspect the existing attempt instead of republishing")
            remote = {file["path"]: file["sha256"] for file in existing["files"]}
            local = {
                file.relative_to(args.folder).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
                for file in args.folder.rglob("*") if file.is_file()
            }
            if existing["version"] != version or remote != local:
                raise ValueError("the published version differs; bump the shared suite version before releasing")
            print(json.dumps({"status": "unchanged", "name": name, "version": version}))
            return 0
        # A first staged package is invisible even to its owner until publication.
        # Keep accepted receipts: a 404 must never turn that pending version into a new upload.
        receipts = json.loads(Path(__file__).with_name("clawhub-publications.json").read_text())
        accepted = receipts.get(name, {}).get(version)
        if accepted:
            raise ValueError(
                f"ClawHub already accepted {name}@{version} as attempt {accepted['attempt_id']}; "
                "follow that attempt without uploading again"
            )
        # Other errors (network, rate limits, malformed/private pending state) stop the release.
        missing = ("Package not found or not visible to this account.", "Version not found")
        if not any(message in result.stderr for message in missing):
            raise RuntimeError(result.stderr.strip())
    publish = [
        *command, "publish", str(args.folder), "--family", "bundle-plugin", "--bundle-format", "claude",
        "--name", name, "--display-name", "Beancount.io", "--owner", owner, "--version", version,
        "--source-repo", os.environ.get("GITHUB_REPOSITORY", "bex-co/beancount-io"),
        "--source-commit", os.environ.get("GITHUB_SHA") or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "--source-ref", os.environ.get("GITHUB_REF", "refs/heads/main"),
        "--source-path", ".", "--json",
    ]
    if args.mode == "preview":
        publish.append("--dry-run")
    else:
        publish += ["--changelog", f"Beancount.io suite {version}", "--wait", "--wait-timeout", "1200"]
    return subprocess.run(publish, check=False).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        sys.exit(1)
