"""Intent classifier node. One small LLM call; falls back to deterministic
keyword rules when the LLM is unavailable or the output is not parseable.

Categories: support | complaint | greeting | off_topic | escalation_request"""
from __future__ import annotations

import json
import re

from app.core.logging import logger
from app.services.llm_service import complete
from app.services.workflow.types import WorkflowState

_ESCALATE_WORDS = ("manager", "supervisor", "human", "complaint", "refund immediately",
                   "speak to someone", "talk to a person", "escalate", "lawsuit", "legal")
_DOMAIN_WORDS = ("order", "return", "refund", "shipping", "warranty", "support", "product",
                 "account", "payment", "delivery", "track", "tracking", "cancel", "issue",
                 "problem", "invoice", "damaged", "defective", "policy", "exchange", "bill", "price")
_GREETINGS_RE = re.compile(r"^(?:hello|hi|hey|good morning|good evening|hiya|howdy|yo|how are you)\b")
_GREETING_ONLY = frozenset({"thanks", "thank you", "ty", "thx"})


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def _has_domain_signal(text: str) -> bool:
    return "?" in text or any(_has_word(text, w) for w in _DOMAIN_WORDS)


async def _llm_intent(message: str) -> tuple[str | None, float]:
    messages = [
        {"role": "system", "content": (
            "Classify this customer support message into exactly one category: "
            "support, complaint, greeting, off_topic, escalation_request. "
            "Reply with only valid JSON: {\"intent\": \"<category>\", \"confidence\": <0.0-1.0>}")},
        {"role": "user", "content": f"Customer message: {message}"},
    ]
    try:
        raw = await complete(messages)
        data = json.loads(raw.strip())
        intent = data.get("intent")
        if intent not in ("support", "complaint", "greeting", "off_topic", "escalation_request"):
            return "support", 1.0
        return intent, float(data.get("confidence", 0.0))
    except Exception as exc:  # noqa: BLE001 — grader is best-effort
        logger.warning("intent classifier LLM failed (%s); using keyword fallback", exc)
        return None, 0.0


def _keyword_intent(message: str) -> tuple[str, float]:
    m = message.lower()

    # Escalation language trumps everything else.
    if any(_has_word(m, w) for w in _ESCALATE_WORDS):
        return "escalation_request", 0.7

    # Anything actionable/domain-scoped is a support query. This check runs
    # BEFORE greetings so substring matches ("hey" inside "they") can never
    # make a real question get answered with "how can I help you?".
    if _has_domain_signal(m):
        return "support", 0.5

    stripped = m.strip()
    if _GREETINGS_RE.match(stripped) and len(stripped.split()) <= 8:
        return "greeting", 0.8
    if stripped in _GREETING_ONLY:
        return "greeting", 0.8
    if len(stripped.split()) <= 6:
        return "off_topic", 0.6
    return "support", 0.5


async def intent_classifier(state: WorkflowState) -> WorkflowState:
    state.node_history.append("INTENT_CLASSIFIER")
    intent, conf = await _llm_intent(state.customer_message)
    if not intent:
        intent, conf = _keyword_intent(state.customer_message)
    state.intent = intent
    state.intent_confidence = conf
    return state