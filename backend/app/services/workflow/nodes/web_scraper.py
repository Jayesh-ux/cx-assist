"""SSRF-safe web scraper node — the ONLY place the app fetches remote content.

Security requirements (mandatory, from the audit's crawler finding):
- HTTPS only.
- Domain allowlisted to the brand's OWN admin-set website_url host — never
  user- or request-supplied.
- Resolves the hostname and blocks private/link-local ranges before fetching
  (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16,
  ::1/128, fc00::/7) to stop SSRF into internal services / cloud metadata.
- No redirects (DNS rebinding + redirect-to-internal bypass).
- Content-Type must be HTML.
- Max one scrape per brand per 10 minutes (Redis/in-memory cooldown).
- There is no public API route for this node — it is only reached via the
  workflow runner when the brand KB has no relevant documents.
"""
from __future__ import annotations

import ipaddress
import socket
import urllib.parse

import httpx

from app.core.logging import logger
from app.core.redis_client import cache_get, cache_set
from app.core.config import settings
from app.services.workflow.types import KBChunk, WorkflowState

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]
_MAX_CHUNKS = 15
_COOLDOWN_S = 600


def is_safe_url(url: str, allowed_domain: str) -> bool:
    """SSRF mitigation: scheme + domain allowlist + resolved-IP blocklist."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            return False
        if parsed.netloc != allowed_domain:
            return False
        ip = socket.gethostbyname(parsed.netloc)
        addr = ipaddress.ip_address(ip)
        return not any(addr in net for net in _BLOCKED_NETWORKS)
    except Exception:
        return False


async def _fetch_html(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            resp = await client.get(url, headers={"User-Agent": "CX-Assistant/1.0 (internal)"})
        if resp.status_code != 200:
            logger.warning("scraper status %s for %s", resp.status_code, url)
            return None
        if "text/html" not in resp.headers.get("content-type", ""):
            logger.warning("scraper non-HTML content-type for %s", url)
            return None
        return resp.text
    except Exception as exc:  # noqa: BLE001
        logger.warning("scraper fetch failed %s: %s", url, exc)
        return None


def _extract(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["nav", "footer", "header", "script", "style", "aside", "iframe", "form"]):
        tag.decompose()
    chunks: list[str] = []
    seen: set[str] = set()
    for el in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = el.get_text(strip=True)
        if not (30 < len(text) < 500):
            continue
        if text in seen:
            continue
        seen.add(text)
        chunks.append(text)
        if len(chunks) >= _MAX_CHUNKS:
            break
    return "\n\n".join(chunks)


async def web_scraper(state: WorkflowState) -> WorkflowState:
    state.node_history.append("WEB_SCRAPER")
    if not settings.workflow_scrape_enabled:
        state.errors.append("scraping disabled by config")
        return state

    if not state.website_url:
        state.errors.append("no website_url configured for brand")
        return state

    cooldown_key = f"scrape_cooldown:{state.brand_id}"
    if cache_get(cooldown_key):
        state.errors.append("scrape rate limited (10-minute cooldown)")
        return state

    parsed = urllib.parse.urlparse(state.website_url if "//" in state.website_url else f"https://{state.website_url}")
    allowed_domain = parsed.netloc
    for target_path in ("/help", "/support", "/faq"):
        help_url = f"https://{allowed_domain}{target_path}"
        if not is_safe_url(help_url, allowed_domain):
            state.errors.append(f"URL failed SSRF safety check: {help_url}")
            continue
        html = await _fetch_html(help_url)
        if not html:
            continue
        body = _extract(html)
        if len(body) < 60:
            continue
        state.scraped_content = body
        state.scrape_used = True
        # Feed the scraped page through the SAME grading path in the runner.
        state.retrieved_chunks.append(KBChunk(
            id=f"scrape-{allowed_domain}-{target_path.strip('/')}",
            title=help_url, content=body, category="web", score=0.5, source=help_url,
        ))
        cache_set(cooldown_key, "1", ttl=_COOLDOWN_S)
        return state

    state.errors.append("no scannable help page found for brand website")
    return state