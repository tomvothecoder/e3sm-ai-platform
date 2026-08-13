"""Optional LivAI generator integration with deterministic fallback."""

from __future__ import annotations

from typing import Protocol
from urllib.parse import urlparse

import httpx

from e3sm_assist.generation import generate_response
from e3sm_assist.models import Evidence, QueryResponse, RouteName
from e3sm_assist.settings import Settings

# Deterministic context bound so prompts cannot grow without limit as corpus/retrieval expands.
MAX_EVIDENCE_PROMPT_CHARS = 8_000


class LivAIProviderError(RuntimeError):
    """Sanitized provider error for public debug metadata and fallback control."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ChatClient(Protocol):
    """Small provider-independent chat completion boundary."""

    def complete(self, messages: list[dict[str, str]]) -> str:
        """Return assistant text for chat messages."""


class LivAIChatClient:
    """Minimal OpenAI-compatible LivAI chat client using httpx."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._validate_https_base_url()
        self._client = http_client or httpx.Client(timeout=timeout_seconds)
        self._owns_client = http_client is None

    def close(self) -> None:
        """Close the owned httpx client when the application lifecycle ends."""

        if self._owns_client:
            self._client.close()

    def complete(self, messages: list[dict[str, str]]) -> str:
        self._validate_https_base_url()
        endpoint = self.base_url.rstrip("/") + "/v1/chat/completions"
        payload: dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            response = self._client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise LivAIProviderError(f"http_status_{exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise LivAIProviderError("http_transport_error") from exc
        except ValueError as exc:
            raise LivAIProviderError("invalid_json") from exc
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LivAIProviderError("missing_choices")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise LivAIProviderError("missing_message")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LivAIProviderError("empty_content")
        return content.strip()

    def _validate_https_base_url(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise LivAIProviderError("invalid_https_base_url")


class LivAIEvidenceGenerator:
    """Curated-route LivAI generator preserving server citations/evidence."""

    def __init__(self, client: ChatClient) -> None:
        self.client = client

    def __call__(
        self,
        question: str,
        route: RouteName,
        evidence: list[Evidence],
        include_evidence: bool,
        reason: str,
    ) -> QueryResponse:
        if route is not RouteName.CURATED_RAG or not evidence:
            return generate_response(question, route, evidence, include_evidence, reason)

        fallback = generate_response(question, route, evidence, include_evidence, reason)
        try:
            answer = self.client.complete(build_livai_messages(question, evidence))
        except Exception as exc:
            fallback.debug["livai_fallback"] = True
            fallback.debug["livai_error"] = exc.__class__.__name__
            if isinstance(exc, LivAIProviderError):
                fallback.debug["livai_error_code"] = exc.code
            return fallback

        fallback.answer = answer + "\n\nI have not added claims beyond the cited E3SM sources."
        fallback.debug["livai_used"] = True
        return fallback


def build_livai_messages(question: str, evidence: list[Evidence]) -> list[dict[str, str]]:
    """Build a source-constrained prompt for LivAI."""

    evidence_text = _truncate_prompt_context("\n\n".join(
        f"Source {index}: {item.source.source_id}\n"
        f"Title: {item.source.title}\n"
        f"Section: {item.source.section}\n"
        f"Provenance: {item.source.provenance}\n"
        f"Text: {item.text}"
        for index, item in enumerate(evidence, start=1)
    ))
    return [
        {
            "role": "system",
            "content": (
                "You are E3SM-ASSIST. Answer only from the provided E3SM evidence. "
                "Do not add claims beyond the sources. If the evidence is insufficient, say so. "
                "Do not invent citations; the server attaches citations separately."
            ),
        },
        {
            "role": "user",
            "content": f"Question: {question}\n\nAccepted E3SM evidence:\n{evidence_text}",
        },
    ]


def build_generator(settings: Settings) -> LivAIEvidenceGenerator | None:
    """Return LivAI generator only when explicitly enabled and configured."""

    if not settings.livai_enabled:
        return None
    assert settings.livai_api_key is not None
    client = LivAIChatClient(
        api_key=settings.livai_api_key,
        model=settings.livai_model,
        base_url=settings.livai_base_url,
    )
    return LivAIEvidenceGenerator(client)


def _truncate_prompt_context(text: str) -> str:
    if len(text) <= MAX_EVIDENCE_PROMPT_CHARS:
        return text
    suffix = "\n[Evidence context truncated deterministically at configured character limit.]"
    return text[: MAX_EVIDENCE_PROMPT_CHARS - len(suffix)].rstrip() + suffix
