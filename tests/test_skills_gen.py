import shutil

from context_retrieval_mcp.context_index import Index
from context_retrieval_mcp.skills_gen import generate_skills, GENERATOR_MARKER


def _project(fixture_project, tmp_path):
    project = tmp_path / "proj"
    shutil.copytree(fixture_project, project)
    return project


def test_generation_and_idempotency(fixture_project, tmp_path):
    project = _project(fixture_project, tmp_path)
    index = Index(project)

    result = generate_skills(index)
    assert set(result["written"]) >= {"save-system", "networking"}
    # Legacy doc has no description/keywords -> skipped with warning
    assert "ui-legacy" in result["skipped"]

    skill = (project / ".claude/skills/ctx-save-system/SKILL.md").read_text()
    assert "name: ctx-save-system" in skill
    assert GENERATOR_MARKER in skill
    assert "  - src/services/save_service.py" in skill
    assert "  - src/services/**" in skill              # dir/ -> dir/**
    assert ".claude/context/save-system.md" in skill   # points to canonical doc
    assert "- .claude/context" not in skill.split("---")[1]  # doc not in paths:

    # Second run: everything up to date, nothing rewritten
    result2 = generate_skills(index)
    assert result2["written"] == []
    assert "save-system" in result2["up_to_date"]


def test_hand_written_skill_never_overwritten(fixture_project, tmp_path):
    project = _project(fixture_project, tmp_path)
    manual = project / ".claude/skills/ctx-save-system/SKILL.md"
    manual.parent.mkdir(parents=True)
    manual.write_text("---\nname: ctx-save-system\n---\nhand-written\n")

    index = Index(project)
    result = generate_skills(index)
    assert manual.read_text().endswith("hand-written\n")
    assert any("hand-written" in w or "untouched" in w for w in result["warnings"])


def test_check_mode_reports_stale_without_writing(fixture_project, tmp_path):
    project = _project(fixture_project, tmp_path)
    index = Index(project)
    result = generate_skills(index, check=True)
    assert set(result["stale"]) >= {"save-system", "networking"}
    assert not (project / ".claude/skills").exists()


def test_prune_removes_orphans_only_with_marker(fixture_project, tmp_path):
    project = _project(fixture_project, tmp_path)
    index = Index(project)
    generate_skills(index)

    # Orphan generated skill (subsystem no longer exists)
    orphan = project / ".claude/skills/ctx-gone/SKILL.md"
    orphan.parent.mkdir(parents=True)
    orphan.write_text(f"---\nname: ctx-gone\nmetadata:\n  {GENERATOR_MARKER}\n---\nx\n")
    # Orphan-looking but hand-written -> must survive
    manual = project / ".claude/skills/ctx-manual/SKILL.md"
    manual.parent.mkdir(parents=True)
    manual.write_text("---\nname: ctx-manual\n---\nmine\n")

    result = generate_skills(index, prune=True)
    assert result["pruned"] == ["ctx-gone"]
    assert not orphan.exists()
    assert manual.exists()


def test_yaml_escaping_and_key_sanitization(fixture_project, tmp_path):
    project = _project(fixture_project, tmp_path)
    doc = project / ".claude/context/tricky.md"
    doc.write_text(
        '---\nsubsystem: "Tricky Key"\n'
        'description: "Sync: deterministic [RNG] with \\"quotes\\""\n'
        "keywords: [tricky]\n---\n# Tricky\n"
    )
    index = Index(project)
    result = generate_skills(index)
    skill_file = project / ".claude/skills/ctx-tricky-key/SKILL.md"
    assert skill_file.exists(), result
    skill = skill_file.read_text()
    desc_line = next(l for l in skill.splitlines() if l.startswith("description: "))
    # Always double-quoted, inner quotes escaped -> valid YAML despite ':' and '['
    assert desc_line.startswith('description: "')
    assert desc_line.endswith('"')
    assert "name: ctx-tricky-key" in skill
    assert any("sanitized" in w for w in result["warnings"])


def test_description_cap_truncates_keywords(fixture_project, tmp_path):
    project = _project(fixture_project, tmp_path)
    doc = project / ".claude/context/bigkw.md"
    keywords = ", ".join(f"keyword-number-{i:03d}" for i in range(200))
    doc.write_text(
        f"---\nsubsystem: bigkw\ndescription: Big keyword doc\nkeywords: [{keywords}]\n---\n# Big\n"
    )
    index = Index(project)
    result = generate_skills(index)
    skill = (project / ".claude/skills/ctx-bigkw/SKILL.md").read_text()
    desc_line = next(l for l in skill.splitlines() if l.startswith("description: "))
    assert len(desc_line) - len("description: ") <= 1536
    assert any("truncated" in w for w in result["warnings"])
