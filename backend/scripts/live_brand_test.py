"""Live dual-brand isolation test — Airtel (telecom) vs HDFC Bank (banking).

Seeds real, publicly-published policies for two real brands into the store and
runs the actual cx workflow against a matrix of in-brand and cross-brand
queries. The purpose is to prove the non-negotiable guardrail: a query asked
to one brand can never retrieve (let alone answer from) the other brand's
policy.

Run:  cd backend && venv/bin/python scripts/live_brand_test.py
Note: generation stage requires a real LLM key (OMNIPATH_API_KEY /
GEMINI_API_KEY). Without one the workflow escalates to human review at
`generation_failed`, which is the correct degraded behaviour — the isolation
and grading layers above it run fully live and deterministic.

Policies are summarised from Airtel's TRAI / Telecom Consumers Charter and
HDFC Bank's Credit Card & RBI liability policies (public documents, 2026).
"""
from __future__ import annotations

import asyncio
import os

os.environ.update({
    "SECRET_KEY": "8" * 42,
    "JWT_SECRET": "9" * 40,
    "DATABASE_URL": "sqlite:///./.live_brand_test.db",
    "REDIS_URL": "redis://localhost:5999/0",
    "ENVIRONMENT": "live-test",
    "GEMINI_API_KEY": "",
    "OMNIPATH_API_KEY": "",
    "WORKFLOW_SCRAPE_ENABLED": "false",
})

from app.services import vector_store  # noqa: E402
from app.services.workflow.runner import run_cx_workflow  # noqa: E402
from app.services.workflow.types import WorkflowState  # noqa: E402

BRANDS = {
    "Airtel": {
        "chunks": [
            "To cancel or disconnect an Airtel broadband connection, log a disconnection request "
            "through official channels (app, website, customer care). Airtel stops rental charges "
            "within 24 hours of your request, and TRAI requires the disconnection to be completed "
            "within seven working days.",
            "Refund of your security deposit is made within 60 days after disconnection of the "
            "connection. If Airtel delays the refund beyond 60 days, interest at 10 percent per "
            "annum is payable on the delayed amount.",
            "Advance Rental Plans (ARP) are non-refundable: if you cancel your Airtel broadband "
            "connection before the agreed tenure matures, the upfront payment is not refunded and "
            "no pro-rata refund for unused months is given.",
            "When the connection is closed, return the modem and router equipment supplied on rent. "
            "Final settlement of all dues (billing and pro-rata charges for the final bill cycle) "
            "is completed within 60 days of receiving your disconnection request.",
            "When you lodge a disconnection or complaint request, Airtel gives you a Service "
            "Request (SR) number via SMS. Keep it as proof; billing and charging complaints are "
            "resolved within four weeks and any adjustment applied within one week of resolution.",
        ],
    },
    "HDFC Bank": {
        "chunks": [
            "If your HDFC Bank credit card is lost or stolen, report and block it immediately. Use "
            "PhoneBanking on 1800 160 / 1800 260, NetBanking block card, MyCards app hotlist, "
            "WhatsApp hotlist on 70700 22222, or SMS Block CC followed by the last four digits of "
            "the card to 7308080808.",
            "Lost-card liability: once you report the loss of your credit card to HDFC Bank within "
            "48 hours, you are not liable for any transaction on that card that occurs after "
            "reporting. You remain fully liable for transactions that occurred before you reported "
            "the loss.",
            "Blocking a lost credit card permanently blocks that card; it does not close your "
            "credit card account. To dispute a fraudulent transaction made on your card, raise a "
            "card transaction dispute separately.",
            "Unauthorised transactions: report within 3 working days of the statement or bank "
            "communication for zero liability when the fault is a third-party breach (not yours and "
            "not the bank's). Reporting between 4 and 7 working days caps your liability at "
            "Rs 10,000 for cards up to Rs 5 lakh limit (Rs 25,000 for higher limits), and beyond "
            "7 working days the customer is fully liable.",
            "Disputes on HDFC Bank credit card charges can be raised online with the last 60 days "
            "of transactions via the dispute form, and a reference number is issued. Grievances "
            "are resolved within 30 days, after which you can approach the Banking Ombudsman of RBI.",
        ],
    },
}

CASES = [
    ("in-brand legit", "Airtel", "How do I disconnect my Airtel broadband and get back my security deposit?"),
    ("in-brand legit", "HDFC Bank", "I lost my credit card, how do I block it and am I liable for charges after reporting?"),
    ("in-brand legit", "HDFC Bank", "I see a charge on my credit card that I never made, how do I dispute it?"),
    ("CROSS-BRAND", "Airtel", "I lost my credit card, can you block it for me?"),
    ("CROSS-BRAND", "HDFC Bank", "How do I cancel my broadband plan and return the modem router?"),
    ("CROSS-BRAND", "HDFC Bank", "How many days to get my deposit refunded after I close my plan?"),
    ("in-brand legit", "Airtel", "What interest do you pay on delayed refunds of my deposit?"),
]


async def main() -> None:
    vector_store.ensure_collection()
    for brand, cfg in BRANDS.items():
        vector_store.upsert_chunks(brand, cfg["chunks"], source="official-policy-2026")

    print(f"{'TYPE':<13} {'BRAND':<10} {'HITS':<5} {'PASSED':<7} {'FINAL':<14} NODE PATH")
    print("-" * 110)
    leaked = []
    for kind, brand, q in CASES:
        hits = vector_store.query(brand=brand, query_text=q, top_k=5)
        if any(h["brand"] != brand for h in hits):
            leaked.append(q)

        state = WorkflowState(
            conversation_id=f"lt-{len(leaked)}-{brand}",
            brand_id=brand.lower().replace(" ", "-"),
            brand_name=brand, customer_message=q,
            customer_name="Test", customer_email="t@test.in",
        )
        out = await run_cx_workflow(state)
        print(f"{kind:<13} {brand:<10} {len(hits):<5} {len(out.passed_chunks):<7} "
              f"{out.final_status:<14} {' -> '.join(out.node_history)}")
        for h in hits[:2]:
            print(f"    hit [{h['brand']}] score={h['score']} :: {h['text'][:85]}")
        print(f"    escalation: {out.errors[-1] if out.errors else 'n/a'}")

    print()
    if leaked:
        print(f"CROSS-BRAND LEAKAGE DETECTED: {leaked}")
    else:
        print("RESULT: PASS — zero cross-brand retrieval across all cases.")
    print("(Generation escalates to human review here only because no LLM key is set)")


if __name__ == "__main__":
    asyncio.run(main())