"""Generate Agent Skills from context-doc front-matter.

For each indexed subsystem this produces a thin skill adapter at
`.claude/skills/ctx-<subsystem>/SKILL.md`:

- `description` (always in context, ~free) = the doc's description plus its
  keywords, budgeted to the platform cap;
- `paths:` globs derived from the doc's `files:` front-matter, so the skill
  auto-loads when the agent works on matching files — the native
  replacement for hand-maintained constitution trigger tables;
- a thin body that points at the canonical doc (single source of truth —
  the spec content is never duplicated into the skill).

Safety: generated files carry a marker in their front-matter and the
generator refuses to overwrite any SKILL.md without it, so hand-written
skills are never touched. `prune` removes generated skills whose subsystem
disappeared. `check` reports what would change (CI mode).

Stdlib-only (hooks/scripts import this without the mcp SDK).
"""

from pathlib import Path

GENERATOR_MARKER = "generated-by: context-skills-gen/v1"
SKILL_PREFIX = "ctx-"
DESCRIPTION_CAP = 1536  # platform cap for description (+when_to_use)


def _render_description(info: dict, warnings: list, key: str) -> str:
    description = (info.get("description") or info.get("name") or key).strip()
    if len(description) > DESCRIPTION_CAP:
        warnings.append(f"{key}: description exceeds {DESCRIPTION_CAP} chars — truncated")
        return description[: DESCRIPTION_CAP - 1] + "…"

    keywords = info.get("keywords") or []
    if not keywords:
        return description
    if description and description[-1] not in ".!?":
        description += "."

    suffix = " Use when working on: "
    budget = DESCRIPTION_CAP - len(description) - len(suffix) - 1
    kept = []
    used = 0
    for kw in keywords:
        cost = len(kw) + (2 if kept else 0)
        if used + cost > budget:
            warnings.append(f"{key}: keyword list truncated to fit the description cap")
            break
        kept.append(kw)
        used += cost
    if not kept:
        return description
    return f"{description}{suffix}{', '.join(kept)}."


def _render_paths(files: list) -> list:
    paths = []
    for f in files:
        if f.startswith(".claude/"):
            continue
        paths.append(f + "**" if f.endswith("/") else f)
    return paths


def render_skill(key: str, info: dict, warnings: list) -> str:
    description = _render_description(info, warnings, key)
    paths = _render_paths(info.get("files") or [])

    lines = [
        "---",
        f"name: {SKILL_PREFIX}{key}",
        f"description: {description}",
    ]
    if paths:
        lines.append("paths:")
        lines.extend(f"  - {p}" for p in paths)
    lines += [
        "metadata:",
        f"  {GENERATOR_MARKER}",
        "---",
        "",
        f"# {info.get('name') or key} (context skill)",
        "",
        description,
        "",
    ]
    if paths:
        lines.append("**Key files:**")
        lines.extend(f"- `{p}`" for p in paths)
        lines.append("")
    doc = info.get("doc") or f".claude/context/{key}.md"
    lines += [
        f"**Full spec:** Read `{doc}` for the complete specification — do not "
        "rely on this summary for implementation details.",
    ]
    related = info.get("related") or []
    if related:
        lines += ["", "Related subsystems: " + ", ".join(f"`{r}`" for r in related) + "."]
    return "\n".join(lines) + "\n"


def generate_skills(index, prune: bool = False, check: bool = False) -> dict:
    """Generate/refresh skills for every indexed subsystem.

    Returns {"written": [], "up_to_date": [], "stale": [], "skipped": [],
    "pruned": [], "warnings": []}. In check mode nothing is written;
    `stale` lists what a real run would change (including prunes).
    """
    result = {"written": [], "up_to_date": [], "stale": [], "skipped": [],
              "pruned": [], "warnings": []}
    skills_dir = index.project_root / ".claude" / "skills"

    expected_dirs = set()
    for key, info in index.subsystems.items():
        if not (info.get("description") or info.get("keywords")):
            result["skipped"].append(key)
            result["warnings"].append(
                f"{key}: no description/keywords (legacy doc?) — no skill generated"
            )
            continue

        skill_dir = skills_dir / f"{SKILL_PREFIX}{key}"
        skill_file = skill_dir / "SKILL.md"
        expected_dirs.add(skill_dir.name)
        content = render_skill(key, info, result["warnings"])

        if skill_file.exists():
            existing = skill_file.read_text(encoding="utf-8")
            if GENERATOR_MARKER not in existing:
                result["skipped"].append(key)
                result["warnings"].append(
                    f"{key}: {skill_file} exists without the generator marker — "
                    "hand-written skill left untouched"
                )
                continue
            if existing == content:
                result["up_to_date"].append(key)
                continue

        if check:
            result["stale"].append(key)
            continue
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(content, encoding="utf-8")
        result["written"].append(key)

    if prune and skills_dir.is_dir():
        for entry in sorted(skills_dir.iterdir()):
            if not entry.is_dir() or not entry.name.startswith(SKILL_PREFIX):
                continue
            if entry.name in expected_dirs:
                continue
            skill_file = entry / "SKILL.md"
            if skill_file.is_file() and GENERATOR_MARKER in skill_file.read_text(encoding="utf-8"):
                if check:
                    result["stale"].append(f"{entry.name} (orphan)")
                    continue
                skill_file.unlink()
                try:
                    entry.rmdir()
                except OSError:  # extra files inside — leave the dir
                    pass
                result["pruned"].append(entry.name)

    return result
