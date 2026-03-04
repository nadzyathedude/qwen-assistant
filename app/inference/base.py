from __future__ import annotations

import abc
from typing import Generator


class InferenceBackend(abc.ABC):
    """Abstract base for all inference backends."""

    @abc.abstractmethod
    def generate_stream(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        repeat_penalty: float = 1.1,
    ) -> Generator[str, None, None]:
        """Yield tokens one at a time as they are produced."""
        ...

    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        repeat_penalty: float = 1.1,
    ) -> str:
        """Non-streaming fallback: collect all tokens and return as one string."""
        chunks: list[str] = []
        for token in self.generate_stream(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            repeat_penalty=repeat_penalty,
        ):
            chunks.append(token)
        return "".join(chunks)

    @abc.abstractmethod
    def close(self) -> None:
        """Release any resources held by this backend."""
        ...
