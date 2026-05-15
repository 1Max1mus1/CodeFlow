"""Automated checks for the MiMo Token Plan China integration."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services.ai import mimo
from src.settings import Settings


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeAsyncClient:
    posts = []

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.get("timeout")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, *, headers, json):
        self.posts.append({"url": url, "headers": headers, "json": json})
        return _FakeResponse(
            {
                "content": [
                    {"type": "text", "text": "generated "},
                    {"type": "text", "text": "content"},
                ]
            }
        )


class _HTTPStatusAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, *, headers, json):
        request = mimo.httpx.Request("POST", url)
        return mimo.httpx.Response(401, request=request, json={"error": "unauthorized"})


class _TimeoutAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, *, headers, json):
        request = mimo.httpx.Request("POST", url)
        raise mimo.httpx.ReadTimeout("timed out", request=request)


def test_messages_url_normalizes_token_plan_cn_endpoint():
    assert (
        mimo._messages_url("https://token-plan-cn.xiaomimimo.com/anthropic")
        == "https://token-plan-cn.xiaomimimo.com/anthropic/v1/messages"
    )
    assert (
        mimo._messages_url("https://token-plan-cn.xiaomimimo.com/anthropic/v1")
        == "https://token-plan-cn.xiaomimimo.com/anthropic/v1/messages"
    )
    assert (
        mimo._messages_url("https://token-plan-cn.xiaomimimo.com/anthropic/v1/messages")
        == "https://token-plan-cn.xiaomimimo.com/anthropic/v1/messages"
    )


def test_convert_messages_splits_system_and_merges_consecutive_roles():
    system, messages = mimo._convert_messages(
        [
            {"role": "system", "content": "system A"},
            {"role": "system", "content": "system B"},
            {"role": "user", "content": "hello"},
            {"role": "user", "content": "more context"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "finish"},
        ]
    )

    assert system == "system A\n\nsystem B"
    assert messages == [
        {"role": "user", "content": "hello\n\nmore context"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "finish"},
    ]


def test_convert_messages_adds_empty_user_message_when_needed():
    system, messages = mimo._convert_messages([{"role": "system", "content": "rules"}])

    assert system == "rules"
    assert messages == [{"role": "user", "content": ""}]


def test_extract_text_supports_anthropic_blocks_and_plain_strings():
    assert mimo._extract_text({"content": "plain"}) == "plain"
    assert (
        mimo._extract_text(
            {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}
        )
        == "ab"
    )


def test_extract_stream_text_delta_supports_anthropic_events():
    line = (
        'data: {"type":"content_block_delta",'
        '"delta":{"type":"text_delta","text":"hello"}}'
    )
    assert mimo._extract_stream_text_delta(line) == "hello"
    assert mimo._extract_stream_text_delta("event: ping") == ""
    assert mimo._extract_stream_text_delta("data: [DONE]") == ""


@pytest.mark.asyncio
async def test_create_posts_anthropic_messages_request(monkeypatch):
    _FakeAsyncClient.posts = []
    monkeypatch.setattr(mimo.httpx, "AsyncClient", _FakeAsyncClient)

    client = mimo.MimoTokenPlanClient(
        api_key="tp-test",
        base_url="https://token-plan-cn.xiaomimimo.com/anthropic",
        timeout_seconds=3,
    )
    completion = await client.chat.completions.create(
        model=mimo.MIMO_MODEL,
        messages=[
            {"role": "system", "content": "be concise"},
            {"role": "user", "content": "write code"},
        ],
        max_tokens=128,
        temperature=0.2,
        metadata={"trace_id": "test"},
    )

    assert completion.choices[0].message.content == "generated content"
    assert len(_FakeAsyncClient.posts) == 1
    post = _FakeAsyncClient.posts[0]
    assert post["url"] == "https://token-plan-cn.xiaomimimo.com/anthropic/v1/messages"
    assert post["headers"]["Authorization"] == "Bearer tp-test"
    assert post["headers"]["anthropic-version"] == mimo.ANTHROPIC_VERSION
    assert post["headers"]["content-type"] == "application/json"
    assert post["json"] == {
        "model": mimo.MIMO_MODEL,
        "max_tokens": 128,
        "messages": [{"role": "user", "content": "write code"}],
        "system": "be concise",
        "temperature": 0.2,
        "metadata": {"trace_id": "test"},
    }


@pytest.mark.asyncio
async def test_create_requires_token_plan_key():
    client = mimo.MimoTokenPlanClient(
        api_key="",
        base_url="https://token-plan-cn.xiaomimimo.com/anthropic",
        timeout_seconds=3,
    )

    with pytest.raises(RuntimeError, match="XIAOMI_TOKEN_PLAN_CN_API_KEY"):
        await client.chat.completions.create(
            model=mimo.MIMO_MODEL,
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=16,
        )


@pytest.mark.asyncio
async def test_create_maps_auth_error_to_user_facing_mimo_error(monkeypatch):
    monkeypatch.setattr(mimo.httpx, "AsyncClient", _HTTPStatusAsyncClient)

    client = mimo.MimoTokenPlanClient(
        api_key="tp-test",
        base_url="https://token-plan-cn.xiaomimimo.com/anthropic",
        timeout_seconds=3,
    )

    with pytest.raises(mimo.MimoAPIError) as exc_info:
        await client.chat.completions.create(
            model=mimo.MIMO_MODEL,
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=16,
        )

    assert exc_info.value.status_code == 401
    assert "authentication failed" in exc_info.value.user_message
    assert "tp-" in exc_info.value.user_message


@pytest.mark.asyncio
async def test_create_maps_timeout_to_user_facing_mimo_error(monkeypatch):
    monkeypatch.setattr(mimo.httpx, "AsyncClient", _TimeoutAsyncClient)

    client = mimo.MimoTokenPlanClient(
        api_key="tp-test",
        base_url="https://token-plan-cn.xiaomimimo.com/anthropic",
        timeout_seconds=3,
    )

    with pytest.raises(mimo.MimoAPIError) as exc_info:
        await client.chat.completions.create(
            model=mimo.MIMO_MODEL,
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=16,
        )

    assert "timed out" in exc_info.value.user_message


def test_settings_prefers_xiaomi_token_plan_key(monkeypatch):
    monkeypatch.setenv("XIAOMI_TOKEN_PLAN_CN_API_KEY", "tp-primary")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "fallback-token")
    monkeypatch.setenv("MIMO_TOKEN_PLAN_CN_BASE_URL", "https://token-plan-cn.xiaomimimo.com/anthropic")
    monkeypatch.setenv("MIMO_MODEL", "mimo-v2.5-pro")
    monkeypatch.setenv("MIMO_API_TIMEOUT_SECONDS", "123")

    settings = Settings(_env_file=None)

    assert settings.mimo_token_plan_cn_api_key == "tp-primary"
    assert settings.mimo_token_plan_cn_base_url == "https://token-plan-cn.xiaomimimo.com/anthropic"
    assert settings.mimo_model == "mimo-v2.5-pro"
    assert settings.mimo_api_timeout_seconds == 123


def test_settings_keeps_anthropic_auth_token_as_token_plan_fallback(monkeypatch):
    monkeypatch.delenv("XIAOMI_TOKEN_PLAN_CN_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "fallback-token")

    settings = Settings(_env_file=None)

    assert settings.mimo_token_plan_cn_api_key == "fallback-token"


def test_env_example_documents_token_plan_china_contract():
    env_example = Path(__file__).resolve().parents[1] / ".env.example"
    text = env_example.read_text(encoding="utf-8")

    assert "XIAOMI_TOKEN_PLAN_CN_API_KEY=" in text
    assert "MIMO_TOKEN_PLAN_CN_BASE_URL=https://token-plan-cn.xiaomimimo.com/anthropic" in text
    assert "MIMO_MODEL=mimo-v2.5-pro" in text
    assert "MIMO_API_TIMEOUT_SECONDS=120" in text
    assert ("MOON" + "SHOT") not in text
    assert ("OPEN" + "AI") not in text


@pytest.mark.skipif(
    os.environ.get("RUN_MIMO_LIVE_TEST") != "1",
    reason="Set RUN_MIMO_LIVE_TEST=1 to call the real MiMo Token Plan CN API",
)
@pytest.mark.asyncio
async def test_live_mimo_token_plan_cn_smoke():
    if not mimo.SETTINGS.mimo_token_plan_cn_api_key:
        pytest.skip("XIAOMI_TOKEN_PLAN_CN_API_KEY is not configured")

    client = mimo.make_mimo_client()
    completion = await client.chat.completions.create(
        model=mimo.SETTINGS.mimo_model or mimo.MIMO_MODEL,
        messages=[{"role": "user", "content": "Reply with exactly: ok"}],
        max_tokens=16,
        temperature=0,
    )

    assert completion.choices[0].message.content.strip()


def test_repository_has_no_legacy_provider_references():
    repo_root = Path(__file__).resolve().parents[2]
    legacy_patterns = [
        "MOON" + "SHOT",
        "Moon" + "shot",
        "moon" + "shot",
        "Ki" + "mi",
        "ki" + "mi",
        "Open" + "AI",
        "open" + "ai",
        "Async" + "Open" + "AI",
        "api." + "moon" + "shot",
        "platform." + "moon" + "shot",
    ]
    excluded_dirs = {".git", "node_modules", "__pycache__", ".pytest_cache"}
    excluded_files = {".env", "package-lock.json"}
    offenders = []

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in excluded_dirs for part in path.parts):
            continue
        if path.name in excluded_files:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in legacy_patterns:
            if pattern in text:
                offenders.append(f"{path.relative_to(repo_root)} contains {pattern}")

    assert offenders == []
