"""Unit tests for the non-negotiable guardrails layer."""
from app.core.config import settings
from app.core.guardrails import finalize_reply, is_fallback_reply, validate_context_brand


def test_fallback_phrase_detected():
    assert is_fallback_reply("I couldn't find enough info. Please review manually.")
    assert not is_fallback_reply("A normal grounded reply.")


def test_empty_reply_is_ungrounded():
    r = finalize_reply("", 1.0, True)
    assert not r.ok
    assert r.code.value == "ungrounded"


def test_self_reported_insufficient_context_routes_to_review():
    r = finalize_reply("I couldn't find enough info. Please review manually.", 1.0, True)
    assert not r.ok
    assert r.code.value == "no_context"


def test_missing_context_routes_to_review():
    r = finalize_reply("A reply anyway", 1.0, False)
    assert not r.ok
    assert r.code.value == "no_context"


def test_low_confidence_routes_to_review(monkeypatch):
    monkeypatch.setattr(settings, "confidence_threshold", 0.60)
    r = finalize_reply("Yes we can do that", 0.40, True)
    assert not r.ok
    assert r.code.value == "low_confidence"


def test_grounded_high_confidence_passes(monkeypatch):
    monkeypatch.setattr(settings, "confidence_threshold", 0.60)
    r = finalize_reply("Yes we can do that", 0.90, True)
    assert r.ok
    assert r.code.value == "ok"


def test_cross_brand_leak_detected():
    assert validate_context_brand("brand-a", "brand-b") == "cross_brand_leak_detected"
    assert validate_context_brand("brand-a", "brand-a") is None
    assert validate_context_brand(None, "brand-a") is None