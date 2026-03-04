from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


class ConversationBuffer:
    """Fixed-size conversation memory that builds ChatML-formatted prompts."""

    def __init__(self, system_prompt: str, max_turns: int = 20) -> None:
        self._system = system_prompt
        self._max_turns = max_turns
        self._history: list[Message] = []

    @property
    def history(self) -> list[Message]:
        return list(self._history)

    def add_user(self, content: str) -> None:
        self._history.append(Message(role="user", content=content))
        self._trim()

    def add_assistant(self, content: str) -> None:
        self._history.append(Message(role="assistant", content=content))
        self._trim()

    def _trim(self) -> None:
        # Keep at most max_turns pairs (user+assistant = 2 messages per turn)
        max_messages = self._max_turns * 2
        if len(self._history) > max_messages:
            self._history = self._history[-max_messages:]

    def build_prompt(self) -> str:
        """Build a ChatML-formatted prompt string for llama.cpp."""
        parts: list[str] = []
        parts.append(f"<|im_start|>system\n{self._system}<|im_end|>")
        for msg in self._history:
            parts.append(f"<|im_start|>{msg.role}\n{msg.content}<|im_end|>")
        parts.append("<|im_start|>assistant\n")
        return "\n".join(parts)

    def build_history_dicts(self) -> list[dict[str, str]]:
        return [m.to_dict() for m in self._history]

    def clear(self) -> None:
        self._history.clear()
