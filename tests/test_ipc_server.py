import io
import json

from engine.ipc.server import RpcServer


def test_health_and_shutdown_over_line_delimited_io() -> None:
    server = RpcServer()
    calls: list[dict] = []

    def health(_: dict) -> dict:
        calls.append("health")
        return {"status": "ok"}

    def shutdown(_: dict) -> dict:
        calls.append("shutdown")
        server.stop()
        return {"status": "stopping"}

    server.register("health", health)
    server.register("shutdown", shutdown)
    incoming = io.StringIO('{"id":1,"method":"health","params":{}}\n{"id":2,"method":"shutdown","params":{}}\n')
    outgoing = io.StringIO()
    server.run(stdin=incoming, stdout=outgoing)

    lines = [json.loads(line) for line in outgoing.getvalue().splitlines()]
    assert lines[0] == {"id": 1, "result": {"status": "ok"}}
    assert lines[1]["id"] == 2
    assert lines[1]["result"] == {"status": "stopping"}
    assert "shutdown" in calls


def test_unknown_method_returns_error() -> None:
    server = RpcServer()
    response = server.dispatch({"id": "a", "method": "missing", "params": {}})
    assert response is not None
    assert response["error"]["code"] == -32601
