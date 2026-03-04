from __future__ import annotations

import json
import logging
from typing import Generator

import httpx

from app.inference.base import InferenceBackend

logger = logging.getLogger("qwen.remote")


class RemoteBackend(InferenceBackend):
    """Streams tokens from a remote FastAPI inference server via chunked HTTP."""

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: int = 120,
    ) -> None:
        self._url = base_url.rstrip("/") + "/generate"
        self._token = token
        self._timeout = timeout

    def generate_stream(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        repeat_penalty: float = 1.1,
    ) -> Generator[str, None, None]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "repeat_penalty": repeat_penalty,
            "stream": True,
        }

        try:
            with httpx.Client(timeout=httpx.Timeout(self._timeout, connect=10.0)) as client:
                with client.stream("POST", self._url, json=payload, headers=headers) as resp:
                    if resp.status_code == 401:
                        raise PermissionError("Authentication failed: invalid API token")
                    if resp.status_code != 200:
                        body = resp.read().decode(errors="replace")
                        raise RuntimeError(
                            f"Remote server error {resp.status_code}: {body[:500]}"
                        )
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                return
                            try:
                                obj = json.loads(data)
                                token = obj.get("token", "")
                                if token:
                                    yield token
                            except json.JSONDecodeError:
                                logger.warning("Malformed SSE data: %s", data[:100])
        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"Cannot reach remote server at {self._url}: {exc}"
            ) from exc
        except httpx.ReadTimeout as exc:
            raise TimeoutError(
                f"Remote server timed out after {self._timeout}s"
            ) from exc

    def close(self) -> None:
        pass
