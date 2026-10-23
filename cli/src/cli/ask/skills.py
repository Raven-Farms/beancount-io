from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import frontmatter as _fm


@dataclass
class AgentSkill:
    name: str
    description: str
    body: str
    path: Path
    license: str | None = None
    compatibility: str | None = None
    allowed_tools: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    #: Loaded from the working directory's `.agents/skills/`, not the user's own.
    project: bool = False
    #: A project skill that replaced the user's skill of the same name.
    shadows: bool = False
    #: The description was longer than `MAX_DESCRIPTION` and was cut.
    truncated: bool = False


#: A skill's description goes to the model on every turn, so its size is the
#: user's cost; a repository's 2 MB description was sent whole (w5/454).
MAX_DESCRIPTION = 1024
#: The whole skill index, for the same reason: thousands of small skills.
MAX_INDEX = 32 * 1024
#: A loaded skill body stays in the conversation and rides along on every
#: later request; a 2 MB SKILL.md was returned whole (w5/849). The same size
#: as a query result the model is shown.
MAX_BODY = 12_000


def _parse_skill(path: Path) -> AgentSkill | None:
    """Parse a SKILL.md file. Returns None on any parse or validation failure."""
    try:
        # utf-8-sig: a leading BOM would otherwise hide the opening `---` fence.
        post = _fm.load(str(path), encoding="utf-8-sig")
    except Exception:
        return None

    fm = post.metadata
    name = fm.get("name")
    description = fm.get("description")

    if not isinstance(name, str) or not name:
        return None
    if not isinstance(description, str) or not description:
        return None
    truncated = len(description) > MAX_DESCRIPTION
    if truncated:
        description = description[: MAX_DESCRIPTION - 1] + "…"

    raw_tools = fm.get("allowed-tools", "")
    allowed_tools = raw_tools.split() if isinstance(raw_tools, str) else []

    raw_meta = fm.get("metadata", {})
    metadata = {str(k): str(v) for k, v in raw_meta.items()} if isinstance(raw_meta, dict) else {}

    _license = fm.get("license")
    _compat = fm.get("compatibility")
    return AgentSkill(
        name=name,
        description=description,
        body=post.content,
        path=path,
        license=_license if isinstance(_license, str) else None,
        compatibility=_compat if isinstance(_compat, str) else None,
        allowed_tools=allowed_tools,
        metadata=metadata,
        truncated=truncated,
    )


def _load_skills_from_dir(skills_root: Path) -> list[AgentSkill]:
    if not skills_root.is_dir():
        return []
    results: list[AgentSkill] = []
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        skill = _parse_skill(skill_file)
        if skill is not None:
            results.append(skill)
    return results


def load_skills(cwd: Path | None = None) -> list[AgentSkill]:
    """Discover and load skills from project-level and user-level directories.

    Project-level:  <cwd>/.agents/skills/
    User-level:     ~/.config/bea/skills/

    Project-level skills take precedence when names collide.
    Missing dirs and malformed files are silently skipped.
    """
    base = cwd if cwd is not None else Path.cwd()
    project_skills_dir = base / ".agents" / "skills"
    from cli.config import user_skills_dir as config_user_skills_dir

    user_skills_dir = config_user_skills_dir()

    project = _load_skills_from_dir(project_skills_dir)
    user = _load_skills_from_dir(user_skills_dir)
    user_names = {skill.name for skill in user}
    for skill in project:
        skill.project = True
        skill.shadows = skill.name in user_names

    seen: set[str] = set()
    skills: list[AgentSkill] = []

    for skill in project + user:
        if skill.name not in seen:
            seen.add(skill.name)
            skills.append(skill)

    return skills


def project_skills_notice(skills: list[AgentSkill]) -> list[str]:
    """What the user should know about the skills the working directory supplied.

    A repository's `.agents/skills/` was loaded silently: its descriptions
    reach the model on every turn, and a same-named one replaced the user's
    own skill (w5/454). Nothing to say when only the user's skills loaded.
    """
    lines: list[str] = []
    project = [skill for skill in skills if skill.project]
    if project:
        named = ", ".join(
            f"{skill.name} (replaces your {skill.name})" if skill.shadows else skill.name for skill in project
        )
        lines.append(
            f"Loaded {len(project)} project skill(s) from .agents/skills in the working directory: {named}. "
            "Their descriptions are sent to the model on every turn; run ask only in a directory you trust."
        )
    for skill in skills:
        if skill.truncated:
            lines.append(f"Skill {skill.name!r}: description cut to {MAX_DESCRIPTION} characters.")
    if len(build_skills_index_prompt(skills)) >= MAX_INDEX and _listed(skills) < len(skills):
        lines.append(
            f"Skill index limited to {MAX_INDEX} characters: {len(skills) - _listed(skills)} skill(s) not listed."
        )
    return lines


def _listed(skills: list[AgentSkill]) -> int:
    """How many skills fit the index before `MAX_INDEX`."""
    size = 0
    for count, skill in enumerate(skills):
        size += len(_index_line(skill)) + 1
        if size > MAX_INDEX:
            return count
    return len(skills)


def _index_line(skill: AgentSkill) -> str:
    return f"- **{skill.name}**: {skill.description}"


def build_skills_index_prompt(skills: list[AgentSkill]) -> str:
    """Return a lightweight skill index for the system prompt (name + description only).

    Full skill bodies are intentionally omitted here — the agent fetches them on demand
    via the get_skill_body tool, keeping startup token cost near zero.
    """
    if not skills:
        return ""

    lines: list[str] = [
        "",
        "---",
        "",
        "## Available Agent Skills",
        "",
        "The following skills are available. Call `get_skill_body` with a skill name to load its",
        "full instructions before applying it.",
        "",
    ]
    lines.extend(_index_line(skill) for skill in skills[: _listed(skills)])

    return "\n".join(lines)
