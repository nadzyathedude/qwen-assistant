from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    """Load .env from project root, if present."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)


_load_env()


@dataclass(frozen=True, slots=True)
class Config:
    mode: str = field(default_factory=lambda: os.getenv("MODE", "local"))
    llama_cpp_path: str = field(
        default_factory=lambda: os.getenv("LLAMA_CPP_PATH", "./llama.cpp/build/bin/llama-cli")
    )
    model_path: str = field(
        default_factory=lambda: os.getenv("MODEL_PATH", "./models/qwen.gguf")
    )
    max_tokens: int = field(
        default_factory=lambda: int(os.getenv("MAX_TOKENS", "512"))
    )
    temperature: float = field(
        default_factory=lambda: float(os.getenv("TEMPERATURE", "0.7"))
    )
    top_p: float = field(
        default_factory=lambda: float(os.getenv("TOP_P", "0.9"))
    )
    repeat_penalty: float = field(
        default_factory=lambda: float(os.getenv("REPEAT_PENALTY", "1.1"))
    )
    gpu_layers: int = field(
        default_factory=lambda: int(os.getenv("GPU_LAYERS", "0"))
    )
    ctx_size: int = field(
        default_factory=lambda: int(os.getenv("CTX_SIZE", "4096"))
    )
    threads: int = field(
        default_factory=lambda: int(os.getenv("THREADS", "4"))
    )
    remote_url: str = field(
        default_factory=lambda: os.getenv("REMOTE_URL", "http://127.0.0.1:8000")
    )
    api_token: str = field(
        default_factory=lambda: os.getenv("API_TOKEN", "changeme")
    )
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    timeout: int = field(
        default_factory=lambda: int(os.getenv("TIMEOUT", "120"))
    )
    system_prompt: str = field(
        default_factory=lambda: os.getenv(
            "SYSTEM_PROMPT", "You are a helpful assistant. Answer concisely and accurately."
        )
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )

    def validate(self) -> None:
        if self.mode not in ("local", "remote"):
            raise ValueError(f"MODE must be 'local' or 'remote', got '{self.mode}'")
        if self.mode == "local":
            if not Path(self.llama_cpp_path).exists():
                raise FileNotFoundError(
                    f"llama.cpp binary not found: {self.llama_cpp_path}"
                )
            if not Path(self.model_path).exists():
                raise FileNotFoundError(f"Model file not found: {self.model_path}")
        if self.max_tokens < 1:
            raise ValueError("MAX_TOKENS must be >= 1")
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("TEMPERATURE must be between 0.0 and 2.0")
