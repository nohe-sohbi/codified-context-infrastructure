from context_retrieval_mcp.context_index import parse_front_matter


def test_full_front_matter():
    text = (
        "---\n"
        "subsystem: save-system\n"
        "name: Save System\n"
        "description: Two-tier save architecture\n"
        "keywords: [save, persistence, autosave]\n"
        "files:\n"
        "  - src/services/save_service.py\n"
        "  - src/services/\n"
        "priority: high\n"
        "version: 2\n"
        "last-verified: 2026-08-08\n"
        "---\n"
        "# Save System\n\nBody.\n"
    )
    meta, body, warnings = parse_front_matter(text)
    assert meta["subsystem"] == "save-system"
    assert meta["keywords"] == ["save", "persistence", "autosave"]
    assert meta["files"] == ["src/services/save_service.py", "src/services/"]
    assert meta["version"] == 2
    assert meta["last-verified"] == "2026-08-08"
    assert body.startswith("# Save System")
    assert warnings == []


def test_quoted_multiword_keyword():
    meta, _, warnings = parse_front_matter(
        '---\nkeywords: [sync, "damage report"]\n---\nbody'
    )
    assert meta["keywords"] == ["sync", "damage report"]
    assert warnings == []


def test_legacy_header_fallback():
    meta, body, warnings = parse_front_matter(
        "<!-- v3 | last-verified: 2026-02-15 -->\n# Title\n\nBody.\n"
    )
    assert meta["version"] == 3
    assert meta["last-verified"] == "2026-02-15"
    assert meta["_legacy_header"] is True
    assert body.startswith("# Title")
    assert warnings == []


def test_no_metadata():
    meta, body, warnings = parse_front_matter("# Just a Doc\n\nText.\n")
    assert meta == {}
    assert body.startswith("# Just a Doc")


def test_unclosed_front_matter_warns():
    meta, _, warnings = parse_front_matter("---\nsubsystem: x\nno closing fence\n")
    assert meta == {}
    assert any("never closed" in w for w in warnings)


def test_unsupported_lines_warn_not_silently_parse():
    text = (
        "---\n"
        "subsystem: broken\n"
        "free text with no colon !!\n"
        "nested:\n"
        "  map: value\n"
        "---\nbody"
    )
    meta, _, warnings = parse_front_matter(text)
    assert meta["subsystem"] == "broken"
    # 'nested:' opens a (never-filled) list; the indented map line must warn
    assert any("unsupported" in w for w in warnings)


def test_empty_inline_list_and_booleans():
    meta, _, _ = parse_front_matter("---\nrelated: []\nflag: true\n---\nbody")
    assert meta["related"] == []
    assert meta["flag"] is True


def test_bom_and_crlf_normalized():
    text = "﻿---\r\nsubsystem: bom-doc\r\nkeywords: [a, b]\r\n---\r\n# T\r\nBody.\r\n"
    meta, body, warnings = parse_front_matter(text)
    assert meta["subsystem"] == "bom-doc"
    assert meta["keywords"] == ["a", "b"]
    assert body.startswith("# T")
    assert warnings == []


def test_unicode_digits_never_crash():
    # '²'.isdigit() is True but int('²') raises; '--3' likewise
    meta, _, _ = parse_front_matter("---\nversion: ²\nother: --3\n---\nbody")
    assert meta["version"] == "²"
    assert meta["other"] == "--3"


def test_quoted_item_with_comma_survives():
    meta, _, warnings = parse_front_matter(
        '---\nkeywords: [a, "hello, world", b, \'x, y\']\n---\nbody'
    )
    assert meta["keywords"] == ["a", "hello, world", "b", "x, y"]
    assert warnings == []


def test_double_empty_items_dropped():
    meta, _, _ = parse_front_matter("---\nkeywords: [a,,b, ]\n---\nbody")
    assert meta["keywords"] == ["a", "b"]


def test_horizontal_rule_start_is_not_a_fence():
    meta, body, warnings = parse_front_matter("----\n# Doc\nBody.\n")
    assert meta == {}
    assert warnings == []  # no bogus "never closed" warning
