"""Provider plumbing for the LLM service (configurable URL, keyless routers,
provider selection, Gemini fallback)."""
import asyncio
import json

import httpx

from app.services import llm_service
from app.services.llm_service import complete


class _FakeClient:
    """httpx.AsyncClient stand-in that routes through httpx.MockTransport."""

    def __init__(self, handler, *_args, **_kwargs):
        self._transport = httpx.MockTransport(handler)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, *, params=None, json=None, headers=None):
        request = httpx.Request("POST", url, params=params, json=json, headers=headers)
        return self._transport.handle_request(request)


def _capture(monkeypatch):
    """Install the fake client and return a recorder for outgoing requests."""
    captured = {}

    def handler(request):
        captured["request"] = request
        if request.url.host == "generativelanguage.googleapis.com":
            return httpx.Response(
                200,
                json={"candidates": [{"content": {"parts": [{"text": "Hi from Gemini"}]}}]},
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Hi from router"}}],
                "usage": {"total_tokens": 12},
            },
            request=request,
        )

    monkeypatch.setattr(llm_service.httpx, "AsyncClient", lambda *a, **k: _FakeClient(handler, *a, **k))
    return captured


def test_omniroute_posts_to_configured_url_keyless_auto(monkeypatch):
    captured = _capture(monkeypatch)
    settings = llm_service.settings
    old = (settings.omnipath_url, settings.omnipath_api_key, settings.llm_model)
    try:
        settings.omnipath_url = "http://router.local:20128/v1/chat/completions"
        settings.omnipath_api_key = ""
        settings.llm_model = ""
        text = asyncio.run(llm_service._call_omniroute([{"role": "user", "content": "hi"}], 0.0, 50))
    finally:
        settings.omnipath_url, settings.omnipath_api_key, settings.llm_model = old

    req = captured["request"]
    assert str(req.url).startswith("http://router.local:20128/v1/chat/completions")
    assert "Authorization" not in req.headers
    assert json.loads(req.content)["model"] == "auto"
    assert text["text"] == "Hi from router"


def test_omniroute_sends_key_and_model_when_configured(monkeypatch):
    captured = _capture(monkeypatch)
    settings = llm_service.settings
    old = (settings.omnipath_url, settings.omnipath_api_key, settings.llm_model)
    try:
        settings.omnipath_url = "https://gateway.test/v1/chat/completions"
        settings.omnipath_api_key = "k123"
        settings.llm_model = "pol/any-free-model"
        asyncio.run(llm_service._call_omniroute([{"role": "user", "content": "hi"}], 0.0, 50))
    finally:
        settings.omnipath_url, settings.omnipath_api_key, settings.llm_model = old

    req = captured["request"]
    assert req.headers["Authorization"] == "Bearer k123"
    assert json.loads(req.content)["model"] == "pol/any-free-model"


def test_complete_uses_only_gemini_when_provider_gemini(monkeypatch):
    captured = _capture(monkeypatch)
    settings = llm_service.settings
    old = (settings.llm_provider, settings.gemini_api_key, settings.llm_model)
    try:
        settings.llm_provider = "gemini"
        settings.gemini_api_key = "g123"
        settings.llm_model = ""
        text = asyncio.run(complete([{"role": "user", "content": "hi"}]))
    finally:
        settings.llm_provider, settings.gemini_api_key, settings.llm_model = old

    assert text == "Hi from Gemini"
    assert "gemini-2.5-flash" in str(captured["request"].url)
    assert "key=g123" in str(captured["request"].url)
    assert llm_service.last_provider() == "gemini"


def test_complete_auto_uses_router_then_gemini_fallback(monkeypatch):
    """LLM_PROVIDER=auto uses the router and falls back to Gemini when it fails."""

    def handler(request):
        if "generativelanguage.googleapis.com" in str(request.url):
            return httpx.Response(
                200,
                json={"candidates": [{"content": {"parts": [{"text": "Gemini fallback text"}]}}]},
                request=request,
            )
        return httpx.Response(503, request=request)

    monkeypatch.setattr(llm_service.httpx, "AsyncClient", lambda *a, **k: _FakeClient(handler))
    settings = llm_service.settings
    old = (settings.llm_provider, settings.gemini_api_key, settings.omnipath_url, settings.omnipath_api_key, settings.llm_model)
    try:
        settings.llm_provider = "auto"
        settings.gemini_api_key = "g123"
        settings.omnipath_url = "http://router.local:20128/v1/chat/completions"
        settings.omnipath_api_key = "k123"
        settings.llm_model = ""
        text = asyncio.run(complete([{"role": "user", "content": "hi"}]))
    finally:
        (settings.llm_provider, settings.gemini_api_key, settings.omnipath_url,
         settings.omnipath_api_key, settings.llm_model) = old

    assert text == "Gemini fallback text"
    assert llm_service.last_provider() == "gemini"


def test_complete_auto_prefers_router_when_both_work(monkeypatch):
    """LLM_PROVIDER=auto uses the router result when both providers are healthy."""

    def handler(request):
        if "generativelanguage.googleapis.com" in str(request.url):
            return httpx.Response(
                200,
                json={"candidates": [{"content": {"parts": [{"text": "Gemini"}]}}]},
                request=request,
            )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Router text"}}], "usage": {"total_tokens": 5}},
            request=request,
        )

    monkeypatch.setattr(llm_service.httpx, "AsyncClient", lambda *a, **k: _FakeClient(handler))
    settings = llm_service.settings
    old = (settings.llm_provider, settings.gemini_api_key, settings.omnipath_url, settings.omnipath_api_key, settings.llm_model)
    try:
        settings.llm_provider = "auto"
        settings.gemini_api_key = "g123"
        settings.omnipath_url = "http://router.local:20128/v1/chat/completions"
        settings.omnipath_api_key = "k123"
        settings.llm_model = ""
        text = asyncio.run(complete([{"role": "user", "content": "hi"}]))
    finally:
        (settings.llm_provider, settings.gemini_api_key, settings.omnipath_url,
         settings.omnipath_api_key, settings.llm_model) = old

    assert text == "Router text"
    assert llm_service.last_provider() == "omniroute"