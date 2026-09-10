"""Unit tests for the intent classifier's deterministic keyword fallback.

Regression coverage for the substring false-positive: "hey" inside "they"
used to classify real customer queries ("Can I return my headphones? They
arrived yesterday.") as a greeting, which answered them with a hello.
"""
import asyncio
import pytest

from app.services.workflow.nodes.intent_classifier import _keyword_intent, intent_classifier
from app.services.workflow.types import WorkflowState


@pytest.mark.parametrize("message,expected", [
    ("Can I return my headphones? They arrived yesterday.", "support"),
    ("I want to return my order now please", "support"),
    ("Where is my refund?", "support"),
    ("What is your return policy", "support"),
    ("My order still shows as pending, please check", "support"),
    ("The product I ordered is damaged", "support"),
    ("I need to speak to a manager", "escalation_request"),
    ("This is a complaint about my invoice", "escalation_request"),
    ("I want to escalate this right now", "escalation_request"),
    ("Hi there", "greeting"),
    ("Hello, how are you today", "greeting"),
    ("thanks", "greeting"),
    ("Good morning", "greeting"),
    ("What a lovely day", "off_topic"),
])
def test_keyword_fallback_maps_correctly(message, expected):
    intent, _conf = _keyword_intent(message)
    assert intent == expected, f"{message!r} -> {intent} (expected {expected})"


def test_no_substring_greeting_false_positive():
    # Regression: "hey" inside "they" must NOT yield a greeting.
    intent, conf = _keyword_intent("Can I return my headphones? They arrived yesterday.")
    assert intent == "support"
    assert conf == 0.5


def test_classifier_node_returns_support_when_llm_down(monkeypatch):
    """LLM unavailable -> keyword fallback must still answer correctly, not crash."""
    async def boom(messages, temperature=None, max_tokens=None, on_complete=None):
        raise RuntimeError("provider down")

    monkeypatch.setattr("app.services.workflow.nodes.intent_classifier.complete", boom)
    state = WorkflowState(
        conversation_id="c1", brand_id="brand-a", brand_name="Acme",
        customer_message="Can I return my headphones? They arrived yesterday.",
        customer_name="Jay", customer_email="j@x.com",
    )
    out = asyncio.run(intent_classifier(state))
    assert out.intent == "support"
    assert "INTENT_CLASSIFIER" in out.node_history