"""Unified keyword/trigger scoring shared by all retrieval tools.

Matching rules (stdlib-only — this module must never import `mcp`, so that
session hooks can import it under a bare python3):

- Single-word terms match on word boundaries: the keyword "ai" matches
  "fix the ai behavior" but NOT "maintain the login page".
- Multi-word phrases match as substrings (word order matters).
- Terms that appear in fewer entries earn a uniqueness bonus, so distinctive
  vocabulary outweighs generic vocabulary shared by many entries.
"""

import re
from typing import Iterable


def tokenize(text: str) -> set:
    """Lowercased word-boundary token set for a task description."""
    return set(re.findall(r"\b\w+\b", text.lower()))


def term_counts(term_lists: Iterable[Iterable[str]]) -> dict:
    """How many entries declare each term (for the uniqueness bonus)."""
    counts: dict = {}
    for terms in term_lists:
        for term in terms:
            counts[term] = counts.get(term, 0) + 1
    return counts


def score_terms(
    task_lower: str,
    task_words: set,
    terms: Iterable[str],
    counts: dict | None = None,
) -> tuple:
    """Score one entry's term list against a task. Returns (score, matched)."""
    score = 0.0
    matched = []
    for term in terms:
        term_words = term.split()
        if len(term_words) == 1:
            hit = term in task_words
        else:
            hit = term in task_lower
        if hit:
            base = len(term_words)
            uniqueness = (1.0 / counts.get(term, 1)) if counts else 0.0
            score += base * (1.0 + uniqueness)
            matched.append(term)
    return score, matched


def description_bonus(task_words: set, description: str) -> float:
    """Weak signal: any task word longer than 3 chars appears in description."""
    desc = description.lower()
    return 0.5 if any(w in desc for w in task_words if len(w) > 3) else 0.0
