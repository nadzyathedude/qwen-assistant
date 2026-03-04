from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import time
from typing import AsyncGenerator

import httpx

logger = logging.getLogger("qwen.server.inference")

_BINARY_DIR = os.path.dirname(os.path.abspath(os.getenv("LLAMA_CPP_PATH", "./llama.cpp/build/bin/llama-cli")))
_SERVER_BINARY = os.path.join(_BINARY_DIR, "llama-server")
_MODEL = os.path.abspath(os.getenv("MODEL_PATH", "./models/qwen.gguf"))
_CTX_SIZE = int(os.getenv("CTX_SIZE", "4096"))
_GPU_LAYERS = int(os.getenv("GPU_LAYERS", "0"))
_THREADS = int(os.getenv("THREADS", "4"))
_TIMEOUT = int(os.getenv("TIMEOUT", "120"))
_INTERNAL_PORT = 8199

_proc: subprocess.Popen[bytes] | None = None


def start_llama_server() -> None:
    """Start llama-server as a persistent subprocess. Called once at app startup."""
    global _proc

    if not os.path.exists(_SERVER_BINARY):
        raise FileNotFoundError(f"llama-server not found: {_SERVER_BINARY}")
    if not os.path.exists(_MODEL):
        raise FileNotFoundError(f"Model not found: {_MODEL}")

    cmd = [
        _SERVER_BINARY,
        "-m", _MODEL,
        "-c", str(_CTX_SIZE),
        "-t", str(_THREADS),
        "--port", str(_INTERNAL_PORT),
        "--host", "127.0.0.1",
        "--log-disable",
    ]
    if _GPU_LAYERS != 0:
        cmd.extend(["-ngl", str(_GPU_LAYERS)])

    logger.info("Starting llama-server: %s", " ".join(cmd))
    _proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    # Wait for healthy.
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(f"http://127.0.0.1:{_INTERNAL_PORT}/health", timeout=2.0)
            if resp.status_code == 200 and resp.json().get("status") == "ok":
                logger.info("llama-server is ready on port %d", _INTERNAL_PORT)
                return
        except (httpx.ConnectError, httpx.ReadError):
            pass
        if _proc.poll() is not None:
            stderr_out = _proc.stderr.read().decode(errors="replace")[-500:] if _proc.stderr else ""
            raise RuntimeError(f"llama-server died on startup (code {_proc.returncode}): {stderr_out}")
        time.sleep(0.5)

    stop_llama_server()
    raise TimeoutError("llama-server did not start within 60s")


def stop_llama_server() -> None:
    global _proc
    if _proc is None:
        return
    try:
        _proc.send_signal(signal.SIGTERM)
        _proc.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            _proc.kill()
            _proc.wait(timeout=3)
        except Exception:
            pass
    _proc = None
    logger.info("llama-server stopped")


async def stream_tokens(
    prompt: str,
    *,
    max_tokens: int = 512,
    temperature: float = 0.7,
    top_p: float = 0.9,
    repeat_penalty: float = 1.1,
) -> AsyncGenerator[str, None]:
    """Proxy a streaming request to the internal llama-server, re-emit as SSE."""
    import asyncio

    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "repeat_penalty": repeat_penalty,
        "stream": True,
        "stop": ["<|im_end|>"],
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(_TIMEOUT, connect=5.0)
        ) as client:
            async with client.stream(
                "POST",
                f"http://127.0.0.1:{_INTERNAL_PORT}/completion",
                json=payload,
            ) as resp:
                if resp.status_code != 200:
                    body = (await resp.aread()).decode(errors="replace")
                    yield f'data: {json.dumps({"error": body[:500]})}\n\n'
                    return
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw.strip() == "[DONE]":
                        break
                    try:
                        obj = json.loads(raw)
                        content = obj.get("content", "")
                        if content:
                            yield f"data: {json.dumps({'token': content})}\n\n"
                        if obj.get("stop", False):
                            break
                    except json.JSONDecodeError:
                        logger.warning("Malformed SSE from llama-server: %s", raw[:100])

        yield "data: [DONE]\n\n"

    except httpx.ConnectError as exc:
        yield f'data: {json.dumps({"error": f"llama-server unreachable: {exc}"})}\n\n'
    except httpx.ReadTimeout:
        yield f'data: {json.dumps({"error": "timeout"})}\n\n'
    except (asyncio.CancelledError, GeneratorExit):
        logger.info("Client disconnected")
