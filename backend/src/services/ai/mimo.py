"""MiMo Token Plan China client using the Anthropic Messages API."""
import json
from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx

from src.settings import SETTINGS

MIMO_TOKEN_PLAN_CN_BASE_URL = "https://token-plan-cn.xiaomimimo.com/anthropic"
MIMO_MODEL = "mimo-v2.5-pro"
ANTHROPIC_VERSION = "2023-06-01"


class MimoAPIError(RuntimeError):
    """User-facing MiMo Token Plan China API failure."""

    def __init__(
        self,
        message: str,
        *,
        user_message: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.user_message = user_message or message
        self.status_code = status_code


@dataclass
class _Message:
    content: str


@dataclass
class _Choice:
    message: _Message


@dataclass
class _Completion:
    choices: list[_Choice]


class MimoTokenPlanClient:
    """Small chat-completions-shaped adapter over MiMo's Anthropic-compatible endpoint."""

    def __init__(self, api_key: str, base_url: str, timeout_seconds: float) -> None:
        self.chat = _Chat(api_key, base_url, timeout_seconds)


class _Chat:
    def __init__(self, api_key: str, base_url: str, timeout_seconds: float) -> None:
        self.completions = _Completions(api_key, base_url, timeout_seconds)


class _Completions:
    def __init__(self, api_key: str, base_url: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._messages_url = _messages_url(base_url)
        self._timeout = httpx.Timeout(timeout_seconds)

    async def create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float | None = None,
        **extra: Any,
    ) -> _Completion:
        if not self._api_key:
            raise MimoAPIError(
                "XIAOMI_TOKEN_PLAN_CN_API_KEY is not configured. "
                "Use a MiMo Token Plan China key that starts with tp-.",
                user_message=(
                    "MiMo Token Plan China API key is not configured. "
                    "Set XIAOMI_TOKEN_PLAN_CN_API_KEY to a Token Plan key that starts with tp-."
                ),
            )

        system_prompt, anthropic_messages = _convert_messages(messages)
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": anthropic_messages,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if temperature is not None:
            payload["temperature"] = temperature
        payload.update(extra)

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self._messages_url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MimoAPIError(
                "MiMo Token Plan China request timed out.",
                user_message=(
                    "MiMo Token Plan China request timed out. "
                    "Please retry or reduce the operation scope."
                ),
            ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise MimoAPIError(
                f"MiMo Token Plan China request failed with HTTP {status_code}.",
                user_message=_http_status_user_message(status_code),
                status_code=status_code,
            ) from exc
        except httpx.RequestError as exc:
            raise MimoAPIError(
                f"MiMo Token Plan China request failed: {exc}",
                user_message=(
                    "Could not connect to MiMo Token Plan China. "
                    "Please check the network connection and retry."
                ),
            ) from exc

        return _Completion(choices=[_Choice(message=_Message(content=_extract_text(response.json())))])

    async def stream(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float | None = None,
        **extra: Any,
    ) -> AsyncIterator[str]:
        if not self._api_key:
            raise MimoAPIError(
                "XIAOMI_TOKEN_PLAN_CN_API_KEY is not configured. "
                "Use a MiMo Token Plan China key that starts with tp-.",
                user_message=(
                    "MiMo Token Plan China API key is not configured. "
                    "Set XIAOMI_TOKEN_PLAN_CN_API_KEY to a Token Plan key that starts with tp-."
                ),
            )

        system_prompt, anthropic_messages = _convert_messages(messages)
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": anthropic_messages,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if temperature is not None:
            payload["temperature"] = temperature
        payload.update(extra)

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
            "accept": "text/event-stream",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    self._messages_url,
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        text = _extract_stream_text_delta(line)
                        if text:
                            yield text
        except httpx.TimeoutException as exc:
            raise MimoAPIError(
                "MiMo Token Plan China streaming request timed out.",
                user_message=(
                    "MiMo Token Plan China request timed out. "
                    "Please retry or reduce the operation scope."
                ),
            ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise MimoAPIError(
                f"MiMo Token Plan China streaming request failed with HTTP {status_code}.",
                user_message=_http_status_user_message(status_code),
                status_code=status_code,
            ) from exc
        except httpx.RequestError as exc:
            raise MimoAPIError(
                f"MiMo Token Plan China streaming request failed: {exc}",
                user_message=(
                    "Could not connect to MiMo Token Plan China. "
                    "Please check the network connection and retry."
                ),
            ) from exc


def make_mimo_client() -> MimoTokenPlanClient:
    return MimoTokenPlanClient(
        api_key=SETTINGS.mimo_token_plan_cn_api_key,
        base_url=SETTINGS.mimo_token_plan_cn_base_url,
        timeout_seconds=SETTINGS.mimo_api_timeout_seconds,
    )


def _messages_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1/messages"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/messages"
    return f"{normalized}/v1/messages"


def _convert_messages(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    system_parts: list[str] = []
    anthropic_messages: list[dict[str, str]] = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        elif role in ("user", "assistant"):
            if anthropic_messages and anthropic_messages[-1]["role"] == role:
                anthropic_messages[-1]["content"] += f"\n\n{content}"
            else:
                anthropic_messages.append({"role": role, "content": content})

    if not anthropic_messages:
        anthropic_messages.append({"role": "user", "content": ""})

    return "\n\n".join(system_parts), anthropic_messages


def _extract_text(payload: dict[str, Any]) -> str:
    content = payload.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return ""


def _extract_stream_text_delta(line: str) -> str:
    if not line.startswith("data:"):
        return ""
    raw = line.removeprefix("data:").strip()
    if not raw or raw == "[DONE]":
        return ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return ""

    if payload.get("type") == "content_block_delta":
        delta = payload.get("delta", {})
        if isinstance(delta, dict) and delta.get("type") == "text_delta":
            return delta.get("text", "")

    if payload.get("type") == "content_block_start":
        content_block = payload.get("content_block", {})
        if isinstance(content_block, dict) and content_block.get("type") == "text":
            return content_block.get("text", "")

    return ""


def _http_status_user_message(status_code: int) -> str:
    if status_code in (401, 403):
        return (
            "MiMo Token Plan China authentication failed. "
            "Check that XIAOMI_TOKEN_PLAN_CN_API_KEY is a valid Token Plan key that starts with tp-."
        )
    if status_code == 429:
        return (
            "MiMo Token Plan China rate limit or quota was reached. "
            "Please retry later or check the Token Plan quota."
        )
    if status_code >= 500:
        return (
            "MiMo Token Plan China service is temporarily unavailable. "
            "Please retry in a moment."
        )
    return f"MiMo Token Plan China request failed with HTTP {status_code}."
