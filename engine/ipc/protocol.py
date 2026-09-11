"""Message shapes for the engine IPC contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RpcRequest:
    id: int | str
    method: str
    params: dict[str, Any]


def make_response(request_id: int | str, result: Any) -> dict[str, Any]:
    return {"id": request_id, "result": result}


def make_error(request_id: int | str | None, code: int, message: str) -> dict[str, Any]:
    return {"id": request_id, "error": {"code": code, "message": message}}


def make_event(name: str, payload: Any) -> dict[str, Any]:
    return {"event": name, "payload": payload}

