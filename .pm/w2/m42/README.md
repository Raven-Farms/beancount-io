# w2 · m42 — Put each customer skill directly under `skills/`

**Worker:** worker2 **Goal:** the customer suite lives at `skills/<name>/SKILL.md`, the conventional skill layout, instead of `skills/.claude/skills/<name>/`. `skills/` holds only the skill folders, a `README.md` catalog, and the `AGENTS.md` authoring guide. Guides and examples move to `docs/skills/`, and the installer, checks, verifiers, routing set, and tests move to `scripts/skills/`. Every existing install survives the move. **Status:** todo (t001 done)

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| [t001](./done/t001.md) | Move every skill folder to `skills/<name>/` — **DONE** | 45m | — |
| t002 | Move the suite's tooling to `scripts/skills/` | 60m | t001 |
| t003 | Move the guides and examples to `docs/skills/` | 45m | t002 |
| t004 | Keep existing installs working across the move | 60m | t002, t003 |
| t005 | Guard the layout in CI and restate the rules | 45m | t001, t002, t003 |
| t006 | Repoint every remaining citation of the old paths | 45m | t001, t003 |
| t007 | Rehearse a fresh install and an upgrade on both clients | 45m | t004, t005, t006 |
| t008 | Adoption surface | 30m | t007 |
| t009 | Simplify | 15m | t008 |
| t010 | Test coverage | 45m | t008, t009 |
| t011 | Closeout | 15m | t010 |

## Definition of done

- `git ls-files skills` lists only `skills/README.md`, `skills/AGENTS.md`, and files under `skills/beancount-*/`. `skills/.claude/` does not exist, and every `skills/beancount-*/` folder has a `SKILL.md`.
- The guides, rehearsal records, and `examples/` sit under `docs/skills/`. The installer, `ci-check.py`, `run-routing.py`, the journey verifiers, `routing.json`, and their tests sit under `scripts/skills/`, with scratch output in the gitignored `scripts/skills/tmp/`.
- A CI check fails when `skills/.claude/` reappears, when a tracked file sits directly in `skills/` other than `README.md` or `AGENTS.md`, or when a folder in `skills/` has no `SKILL.md`. Its unit test proves each case.
- `CI (skills)` and `CI (agent guidance)` trigger on the new paths and pass. `scripts/lint-deadcode.sh` covers the moved `ci-check.py`.
- A fresh install, copied exactly as written from `docs/skills/installation.md`, gives `verify` → `OK` for Claude Code and Codex. An install made from the commit before t001, upgraded with the guide's documented steps, also reaches `OK`. Each client then lists the suite from the upgraded install. Both runs are recorded with versions and dates.
- `install` relinks a link into this checkout's old `skills/.claude/skills/<name>` path. `verify` names that state and the command that repairs it, and `uninstall` removes such links. A link into a different checkout is still reported as a conflict and left alone.
- `git grep 'skills/\.claude'` finds matches only in completed board history (`done/`), the documented upgrade path for old installs, and the installer's old-layout handling and its tests.

## Source + Goal linkage

- **Source:** user request 2026-10-18 via `/pm`: flatten `skills/` so skills sit directly in it, then clean the non-skills out of it. Layout decision, same day: keep `README.md` and `AGENTS.md`, move guides and examples to `docs/skills/` and tooling to `scripts/skills/`.
- **Goal linkage:** **A3 — Community & distribution:** a visitor browsing `skills/` on GitHub sees nine skill folders instead of a `.claude/skills` path that reads as Claude-only, next to unrelated scripts and rehearsal records. The layout is the conventional `skills/<name>/SKILL.md`, which plugin and registry tooling expect ([082](../done/082.md), [w6/m6](../../w6/blocked/m6/README.md)). **A1 — Agent-native accounting:** a nested `.claude/skills` is a location Claude Code can discover while a contributor works under `skills/`. That mixes the customer suite into development sessions, which root `AGENTS.md` keeps separate. The flat layout also has no client-specific directory name, so a Codex user is not left to wonder whether the suite is for them. **A2 — Frictionless onboarding** is the risk to manage: the install command changes, so it must work exactly as written, and every existing install must survive one `git pull`.
- **Expected outcome:** newcomers and registry tooling find the suite at `skills/<name>/`. A user who installed before the move runs the documented upgrade once and keeps a working suite. The repository holds one customer skill tree, with no second `.claude/skills`.
- **Why now:** w6/m6 freezes skill text into immutable ClawHub versions. Two SKILL.md files (`beancount-close`, `beancount-migrate`) link to `skills/docs/installation.md`, which this move relocates. Publishing first would ship links that break permanently. Run after [m40](../blocked/m40/README.md) has committed its `beancount-add` folder, because m40 is mid-flight, so the move carries all nine skills. This milestone does not depend on [m41](../blocked/m41/README.md); whichever lands second rebases onto the other. Adoption surface is included because the install command, every guide path, and the catalog links change.

## Out of scope

- Renaming skills ([m39](../blocked/m39/README.md)), changing what any skill does, or rewriting skill text beyond path strings ([m41](../blocked/m41/README.md)).
- Changing how sibling references resolve ([083](../blocked/083.md)). Relative `../<sibling>/…` paths work the same in the flat layout.
- Packaging the suite as a Claude Code plugin ([082](../done/082.md)) or publishing to ClawHub (w6/m6).
- Redirect stubs at the old paths. GitHub does not redirect moved files, and a stub in `skills/` would be a non-skill file.
- Deploying backend-v2. The MCP prompt text that cites the playbook path changes in the repository here, and reaches hosted clients on the next deploy.
