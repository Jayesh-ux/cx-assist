"""Workflow type definitions for the stateful generate pipeline.

WorkflowState carries everything between nodes. It doubles as the audit trail
(history, errors, prompt) so a single object can be flushed to ai_logs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class KBChunk:
    id: str
    title: str
    content: str
    category: str
    score: float
    source: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "content": self.content,
                "category": self.category, "score": self.score, "source": self.source}


@dataclass
class GradedChunk:
    chunk: KBChunk
    passed: bool
    grader_score: float
    grader_reason: str

    def to_dict(self) -> dict:
        return {"chunk": self.chunk.to_dict(), "passed": self.passed,
                "grader_score": self.grader_score, "grader_reason": self.grader_reason}


@dataclass
class ValidationResult:
    valid: bool
    issues: list[str] = field(default_factory=list)
    correction_hint: str = ""


@dataclass
class WorkflowState:
    # Input (set before the workflow starts)
    conversation_id: str
    brand_id: str
    brand_name: str
    customer_message: str
    customer_name: str
    customer_email: str
    order_context: dict | None = None
    current_user_id: str = ""
    website_url: str = ""  # admin-set brand website (used by the SSRF-safe scraper)

    # Retrieval
    intent: str | None = None
    intent_confidence: float = 0.0
    retrieved_chunks: list[KBChunk] = field(default_factory=list)
    graded_chunks: list[GradedChunk] = field(default_factory=list)
    scraped_content: str | None = None
    scrape_used: bool = False

    # Generation
    generated_response: str | None = None
    citations: list[str] = field(default_factory=list)

    # Validation
    validation_result: ValidationResult | None = None
    correction_attempts: int = 0

    # Output
    final_response: str | None = None
    final_status: str = "pending"  # approved|escalated|deflected|greeting|human_review
    confidence_score: float = 0.0

    # Audit trail
    node_history: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    prompt_text: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def passed_chunks(self) -> list[GradedChunk]:
        return [g for g in self.graded_chunks if g.passed]