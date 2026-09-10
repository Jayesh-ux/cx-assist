"""Unit tests for the document grader.

Covers the crash-safety fix: malformed LLM grades (non-numeric scores, the
string "false", out-of-range indices) must be coerced safely instead of
raising through the whole workflow or being treated as truthy.
"""
from app.services.workflow.nodes.document_grader import _grade_from_scores
from app.services.workflow.types import KBChunk
import pytest


def _chunk(score: float = 0.7) -> KBChunk:
    return KBChunk(id="c1", title="t", content="content", category="faq", score=score)


def test_fallback_uses_retrieval_score():
    graded = _grade_from_scores([_chunk(0.9)], [])
    assert graded[0].passed is True
    assert graded[0].grader_score == 0.9
    assert "fallback" in graded[0].grader_reason


def test_low_retrieval_score_fails():
    graded = _grade_from_scores([_chunk(0.2)], [])
    assert graded[0].passed is False


def test_malformed_llm_grade_never_crashes():
    # String 'false' / garbage score / string index handled defensively.
    chunks = [_chunk(0.9)]
    grades = [{"index": "0", "relevant": "false", "score": "high", "reason": "not relevant"}]
    graded = _grade_from_scores(chunks, grades)
    assert graded[0].passed is False
    assert graded[0].grader_score == 0.0


def test_valid_llm_grade_applies_with_string_score():
    chunks = [_chunk(0.9)]
    grades = [{"index": "0", "relevant": True, "score": "0.9", "reason": "matches"}]
    graded = _grade_from_scores(chunks, grades)
    assert graded[0].passed is True
    assert graded[0].grader_score == pytest.approx(0.9)


def test_out_of_range_index_ignored_falls_back():
    chunks = [_chunk(0.9)]
    grades = [{"index": 7, "relevant": True, "score": 0.9}]
    graded = _grade_from_scores(chunks, grades)
    assert graded[0].passed is True  # fell back to retrieval score
    assert "fallback" in graded[0].grader_reason