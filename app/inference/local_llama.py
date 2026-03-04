from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import time
from typing import Generator

import httpx

from app.inference.base import InferenceBackend

logger = logging.getLogger("qwen.local")

_STARTUP_TIMEOUT = 60  # seconds to wait for llama-server to become healthy
_HEALTH_POLL_INTERVAL = 0.5


class LocalLlamaBackend(InferenceBackend):
    """Runs llama-server as a persistent subprocess and streams via its HTTP API.

    Architecture rationale: llama-server loads the model once and handles
    inference requests over HTTP with built-in SSE streaming.  This avoids the
    per-request model-load overhead of spawning llama-cli and produces clean,
    parseable output with no UI chrome.
    """

    def __init__(
        self,
        llama_cpp_path: str,
        model_path: str,
        ctx_size: int = 4096,
        gpu_layers: int = 0,
        threads: int = 4,
        timeout: int = 120,
    ) -> None:
        # Derive llama-server path from llama-cli path (same directory).
        bin_dir = os.path.dirname(os.path.abspath(llama_cpp_path))
        self._server_binary = os.path.join(bin_dir, "llama-server")
        self._model = os.path.abspath(model_path)
        self._ctx_size = ctx_size
        self._gpu_layers = gpu_layers
        self._threads = threads
        self._timeout = timeout
        self._port = 8199  # Internal port, not exposed externally
        self._base_url = f"http://127.0.0.1:{self._port}"
        self._proc: subprocess.Popen[bytes] | None = None

        self._start_server()

    def _start_server(self) -> None:
        if not os.path.exists(self._server_binary):
            raise FileNotFoundError(
                f"llama-server not found at {self._server_binary}. "
                "Build it with: cmake --build build -- llama-server"
            )

        cmd = [
            self._server_binary,
            "-m", self._model,
            "-c", str(self._ctx_size),
            "-t", str(self._threads),
            "--port", str(self._port),
            "--host", "127.0.0.1",
            "--log-disable",
        ]
        if self._gpu_layers != 0:
            cmd.extend(["-ngl", str(self._gpu_layers)])

        logger.info("Starting llama-server on port %d ...", self._port)
        logger.debug("Command: %s", " ".join(cmd))

        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        # Wait for the server to become healthy.
        deadline = time.monotonic() + _STARTUP_TIMEOUT
        while time.monotonic() < deadline:
            try:
                resp = httpx.get(f"{self._base_url}/health", timeout=2.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "ok":
                        logger.info("llama-server ready")
                        return
            except (httpx.ConnectError, httpx.ReadError):
                pass

            # Check if the process died.
            if self._proc.poll() is not None:
                stderr_out = ""
                if self._proc.stderr:
                    stderr_out = self._proc.stderr.read().decode(errors="replace")[-500:]
                raise RuntimeError(
                    f"llama-server exited during startup (code {self._proc.returncode}): "
                    f"{stderr_out}"
                )

            time.sleep(_HEALTH_POLL_INTERVAL)

        self._kill_proc()
        raise TimeoutError(
            f"llama-server did not become healthy within {_STARTUP_TIMEOUT}s"
        )

    def generate_stream(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        repeat_penalty: float = 1.1,
    ) -> Generator[str, None, None]:
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
            with httpx.Client(
                timeout=httpx.Timeout(self._timeout, connect=5.0)
            ) as client:
                with client.stream(
                    "POST",
                    f"{self._base_url}/completion",
                    json=payload,
                ) as resp:
                    if resp.status_code != 200:
                        body = resp.read().decode(errors="replace")
                        raise RuntimeError(
                            f"llama-server error {resp.status_code}: {body[:500]}"
                        )
                    for line in resp.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            return
                        try:
                            obj = json.loads(data)
                            content = obj.get("content", "")
                            if content:
                                yield content
                            if obj.get("stop", False):
                                return
                        except json.JSONDecodeError:
                            logger.warning("Malformed SSE: %s", data[:100])
        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"Lost connection to llama-server: {exc}"
            ) from exc
        except httpx.ReadTimeout as exc:
            raise TimeoutError(
                f"llama-server timed out after {self._timeout}s"
            ) from exc

    def _kill_proc(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.send_signal(signal.SIGTERM)
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=3)
        except ProcessLookupError:
            pass
        self._proc = None

    def close(self) -> None:
        logger.info("Shutting down llama-server")
        self._kill_proc()
