#!/usr/bin/env python3
"""FastAPI inference server — streams llama.cpp output as SSE."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv

# Load .env before anything reads os.getenv.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from server.auth import BearerAuthMiddleware
from server.inference import start_llama_server, stop_llama_server, stream_tokens

logger = logging.getLogger("qwen.server")
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    start_llama_server()
    yield
    stop_llama_server()
    logger.info("Server shut down")


app = FastAPI(title="Qwen Inference Server", version="1.0.0", lifespan=lifespan)
app.add_middleware(BearerAuthMiddleware)


class GenerateRequest(BaseModel):
    prompt: str
    history: list[dict[str, str]] = Field(default_factory=list)
    max_tokens: int = Field(default=512, ge=1, le=8192)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    repeat_penalty: float = Field(default=1.1, ge=0.0, le=3.0)
    stream: bool = True


def _build_chatml(prompt: str, history: list[dict[str, str]]) -> str:
    """Assemble a ChatML string from history + current prompt."""
    system = os.getenv(
        "SYSTEM_PROMPT",
        "You are a helpful assistant. Answer concisely and accurately.",
    )
    parts = [f"<|im_start|>system\n{system}<|im_end|>"]
    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
    parts.append(f"<|im_start|>user\n{prompt}<|im_end|>")
    parts.append("<|im_start|>assistant\n")
    return "\n".join(parts)


@app.post("/generate")
async def generate(req: GenerateRequest, request: Request) -> StreamingResponse | JSONResponse:
    chatml_prompt = _build_chatml(req.prompt, req.history)

    if not req.stream:
        # Non-streaming fallback: collect all tokens.
        tokens: list[str] = []
        async for chunk in stream_tokens(
            chatml_prompt,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            top_p=req.top_p,
            repeat_penalty=req.repeat_penalty,
        ):
            if chunk.startswith("data: ") and chunk.strip() not in ("data: [DONE]",):
                import json
                try:
                    obj = json.loads(chunk[6:])
                    tokens.append(obj.get("token", ""))
                except json.JSONDecodeError:
                    pass
        return JSONResponse({"text": "".join(tokens)})

    return StreamingResponse(
        stream_tokens(
            chatml_prompt,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            top_p=req.top_p,
            repeat_penalty=req.repeat_penalty,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disables nginx buffering
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    logger.info("Starting server on %s:%d", host, port)
    uvicorn.run(
        "server.app:app",
        host=host,
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        timeout_keep_alive=30,
    )


if __name__ == "__main__":
    main()
