"""Retry/backoff behaviour of the LLM HTTP client (transient 4xx/5xx only)."""
import asyncio
import httpx

from app.services.llm_service import _post_with_retry


def test_retries_transient_then_succeeds():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) <= 2:
            return httpx.Response(429, headers={"Retry-After": "0"}, request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await _post_with_retry(c, "https://x.test/completions", attempts=4)

    resp = asyncio.run(run())
    assert resp.status_code == 200
    assert len(calls) == 3


def test_gives_up_after_attempts():
    def handler(request):
        return httpx.Response(503, request=request)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await _post_with_retry(c, "https://x.test/completions", attempts=2)

    resp = asyncio.run(run())
    assert resp.status_code == 503


def test_does_not_retry_client_error():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(404, request=request)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await _post_with_retry(c, "https://x.test/completions", attempts=3)

    resp = asyncio.run(run())
    assert resp.status_code == 404
    assert len(calls) == 1