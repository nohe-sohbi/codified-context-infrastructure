from context_retrieval_mcp.matching import (
    tokenize, term_counts, score_terms, description_bonus,
)


def _score(task: str, terms, counts=None):
    return score_terms(task.lower(), tokenize(task), terms, counts)


def test_single_word_is_word_boundary_not_substring():
    """The historical bug: keyword 'ai' matched 'maintain' and 'aiming'."""
    score, matched = _score("maintain the login page", ["ai"])
    assert score == 0 and matched == []

    score, matched = _score("improve aiming accuracy", ["ai"])
    assert score == 0 and matched == []

    score, matched = _score("fix the enemy ai behavior", ["ai"])
    assert score > 0 and matched == ["ai"]


def test_multiword_phrase_is_substring_and_order_sensitive():
    score, matched = _score("debug the damage report flow", ["damage report"])
    assert score > 0 and matched == ["damage report"]

    score, matched = _score("report the damage", ["damage report"])
    assert score == 0


def test_multiword_scores_more_than_single():
    single, _ = _score("sync the damage report", ["sync"])
    multi, _ = _score("sync the damage report", ["damage report"])
    assert multi > single


def test_uniqueness_bonus_prefers_rare_terms():
    counts = term_counts([["sync", "desync"], ["sync"], ["sync"]])
    rare, _ = _score("fix the desync now", ["desync"], counts)
    common, _ = _score("fix the sync now", ["sync"], counts)
    assert rare > common


def test_match_code_file_no_suffix_overmatch():
    from drift_common import match_code_file
    assert match_code_file("src/services/save_service.py",
                           ["src/services/save_service.py"])
    assert not match_code_file("vendor/src/services/save_service.py",
                               ["src/services/save_service.py"])
    assert match_code_file("src/network/deep/sync.py", ["src/network/"])
    assert not match_code_file("other/src/network/sync.py", ["src/network/"])


def test_description_bonus_ignores_short_words():
    words = tokenize("fix a db bug")
    assert description_bonus(words, "the db layer") == 0.0  # all words <= 3 chars
    words = tokenize("repair database corruption")
    assert description_bonus(words, "handles database access") == 0.5
