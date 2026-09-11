"""Small bidirectional JSON-RPC server over newline-delimited stdio.

Tauri owns the Python process and exchanges one JSON object per line.
Requests use ``{id, method, params}``; the engine replies with
``{id, result}`` or ``{id, error}`` and may emit ``{event, payload}``.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Callable, Iterable
from typing import Any, TextIO

from engine.ipc.protocol import make_error, make_response

LOGGER = logging.getLogger(__name__)
Handler = Callable[[dict[str, Any]], Any]


class RpcServer:
    def __init__(self, handlers: dict[str, Handler] | None = None) -> None:
        self._handlers = dict(handlers or {})
        self._running = False

    def register(self, method: str, handler: Handler) -> None:
        self._handlers[method] = handler

    def stop(self) -> None:
        self._running = False

    def dispatch(self, message: dict[str, Any]) -> dict[str, Any] | None:
        if "event" in message:
            return None
        request_id = message.get("id")
        method = message.get("method")
        if not isinstance(method, str) or not method:
            return make_error(request_id, -32600, "Invalid request")
        handler = self._handlers.get(method)
        if handler is None:
            return make_error(request_id, -32601, f"Method not found: {method}")
        params = message.get("params", {})
        if not isinstance(params, dict):
            return make_error(request_id, -32602, "Invalid params")
        try:
            return make_response(request_id, handler(params))
        except Exception as exc:  # pragma: no cover - defensive error boundary
            LOGGER.exception("handler %s failed", method)
            return make_error(request_id, -32603, str(exc))

    def run(
        self,
        stdin: TextIO | Iterable[str] | None = None,
        stdout: TextIO | None = None,
    ) -> None:
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        self._running = True
        try:
            if hasattr(stdout, "reconfigure"):
                stdout.reconfigure(line_buffering=True)
        except (AttributeError, OSError):
            pass

        while self._running:
            line = stdin.readline()
            if line == "":
                break
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                response = make_error(None, -32700, f"Parse error: {exc}")
            else:
                if not isinstance(message, dict):
                    response = make_error(None, -32600, "Invalid request")
                else:
                    response = self.dispatch(message)
            if response is not None:
                stdout.write(json.dumps(response, ensure_ascii=False))
                stdout.write("\n")
                stdout.flush()

