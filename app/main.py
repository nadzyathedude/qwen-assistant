#!/usr/bin/env python3
"""Interactive console AI assistant — local or remote inference."""
from __future__ import annotations

import sys

from app.config import Config
from app.inference import InferenceBackend, LocalLlamaBackend, RemoteBackend
from app.utils.logger import get_logger
from app.utils.prompt import ConversationBuffer

BANNER = r"""
 ___                     _         _         _
/ _ \__      _____ _ __ / \   ___ (_)___  __| |
| | | \ \ /\ / / _ \ '_ \  / _ \ / __| / __| __/ _` | '_ \| __  |
| |_| |\ V  V /  __/ | | / ___ \\__ \__ \ |_| (_| | | | | |_  |
 \__\_\ \_/\_/ \___|_| |_/_/   \_\___/|___/\__|\__,_|_| |_|\__|

  Mode: {mode} | /help for commands | Ctrl+C to quit
"""


def _build_backend(cfg: Config) -> InferenceBackend:
    if cfg.mode == "local":
        return LocalLlamaBackend(
            llama_cpp_path=cfg.llama_cpp_path,
            model_path=cfg.model_path,
            ctx_size=cfg.ctx_size,
            gpu_layers=cfg.gpu_layers,
            threads=cfg.threads,
            timeout=cfg.timeout,
        )
    return RemoteBackend(
        base_url=cfg.remote_url,
        token=cfg.api_token,
        timeout=cfg.timeout,
    )


def _handle_command(cmd: str, buf: ConversationBuffer, cfg: Config) -> str | None:
    """Handle slash-commands.  Returns a message to print, or None."""
    cmd = cmd.strip().lower()
    if cmd == "/help":
        return (
            "Commands:\n"
            "  /clear   — reset conversation history\n"
            "  /mode    — show current inference mode\n"
            "  /config  — show active configuration\n"
            "  /quit    — exit the assistant\n"
            "  /help    — show this message"
        )
    if cmd == "/clear":
        buf.clear()
        return "Conversation history cleared."
    if cmd == "/mode":
        return f"Current mode: {cfg.mode}"
    if cmd == "/config":
        lines = [f"  {k} = {v}" for k, v in vars(cfg).items() if not k.startswith("_")]
        return "Active configuration:\n" + "\n".join(lines)
    if cmd in ("/quit", "/exit"):
        raise SystemExit(0)
    return None


def main() -> None:
    cfg = Config()
    log = get_logger("qwen", cfg.log_level)

    try:
        cfg.validate()
    except (FileNotFoundError, ValueError) as exc:
        log.error("Configuration error: %s", exc)
        sys.exit(1)

    backend = _build_backend(cfg)
    buf = ConversationBuffer(system_prompt=cfg.system_prompt)

    print(BANNER.format(mode=cfg.mode))

    try:
        while True:
            try:
                user_input = input("\033[1;32mYou:\033[0m ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                result = _handle_command(user_input, buf, cfg)
                if result is not None:
                    print(result)
                continue

            buf.add_user(user_input)
            prompt = buf.build_prompt()

            sys.stdout.write("\033[1;36mAssistant:\033[0m ")
            sys.stdout.flush()

            response_tokens: list[str] = []
            try:
                for token in backend.generate_stream(
                    prompt,
                    max_tokens=cfg.max_tokens,
                    temperature=cfg.temperature,
                    top_p=cfg.top_p,
                    repeat_penalty=cfg.repeat_penalty,
                ):
                    sys.stdout.write(token)
                    sys.stdout.flush()
                    response_tokens.append(token)
            except TimeoutError:
                log.warning("Inference timed out")
                print("\n[timeout — response truncated]")
            except ConnectionError as exc:
                log.error("Connection error: %s", exc)
                print(f"\n[connection error: {exc}]")
            except RuntimeError as exc:
                log.error("Inference error: %s", exc)
                print(f"\n[error: {exc}]")

            print()  # newline after streamed output
            full_response = "".join(response_tokens)
            if full_response:
                buf.add_assistant(full_response)

    except KeyboardInterrupt:
        print("\nGoodbye.")
    finally:
        backend.close()


if __name__ == "__main__":
    main()
