"""Workflow orchestration. The generate endpoint builds a WorkflowState and
passes it through the node graph; this module owns the routing decisions."""

from __future__ import annotations

from app.services.workflow.nodes.document_grader import document_grader
from app.services.workflow.nodes.document_retriever import document_retriever
from app.services.workflow.nodes.escalate import escalate_node
from app.services.workflow.nodes.intent_classifier import intent_classifier
from app.services.workflow.nodes.response_generator import response_generator
from app.services.workflow.nodes.response_validator import response_validator
from app.services.workflow.nodes.web_scraper import web_scraper
from app.services.workflow.nodes.self_correction import self_correction_node
from app.services.workflow.types import WorkflowState

GREETING_REPLY = "Hi there! Thanks for reaching out. How can I help you today?"
DEFLECT_REPLY = (
    "I'm only able to help with questions about our brand, orders, and support policies. "
    "If you need anything else, I'll connect you with a person."
)


async def _greeting(state: WorkflowState) -> WorkflowState:
    state.node_history.append("GREETING")
    state.final_response = GREETING_REPLY
    state.final_status = "greeting"
    state.confidence_score = 1.0
    return state


async def _deflect(state: WorkflowState) -> WorkflowState:
    state.node_history.append("DEFLECT")
    state.final_response = DEFLECT_REPLY
    state.final_status = "deflected"
    state.confidence_score = 1.0
    return state


async def run_cx_workflow(state: WorkflowState) -> WorkflowState:
    state.node_history.append("START")

    state = await intent_classifier(state)

    if state.intent == "greeting":
        return await _greeting(state)
    if state.intent == "off_topic":
        return await _deflect(state)
    if state.intent == "escalation_request":
        return await escalate_node(state, "escalation_requested_by_customer")

    # 1) retrieve (brand-scoped) -> 2) grade
    state = await document_retriever(state)
    state = await document_grader(state)

    # 3) if nothing passed grading, try the SSRF-safe scraped help page as fallback
    if not state.passed_chunks:
        state = await web_scraper(state)
        if state.scrape_used and state.retrieved_chunks:
            state = await document_grader(state)

    if not state.passed_chunks:
        return await escalate_node(state, "no_relevant_knowledge")

    # 4) generate using ONLY graded/passing chunks
    state = await response_generator(state)
    if not state.generated_response:
        return await escalate_node(state, "generation_failed")

    # 5) validate (guardrails + optional adversarial LLM reviewer)
    state = await response_validator(state)
    if state.validation_result and state.validation_result.valid:
        state.final_status = "approved"
        state.final_response = state.generated_response
        return state

    # 6) one self-correction pass, then re-validate
    state = await self_correction_node(state)
    state = await response_validator(state)
    if state.validation_result and state.validation_result.valid:
        state.final_status = "approved"
        state.final_response = state.generated_response
        return state

    return await escalate_node(state, "validation_failed_after_correction")