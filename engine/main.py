"""Entry point for the Python engine sidecar."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

from engine import __version__
from engine.config import EngineConfig
from engine.db.init_db import init_schema
from engine.ipc.server import RpcServer

LOGGER = logging.getLogger("aisounder.engine")


def _build_server(cfg: EngineConfig) -> RpcServer:
    server = RpcServer()

    def health(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "ok",
            "version": __version__,
            "db_url": cfg.db_url,
            "ducking_enabled": cfg.ducking_enabled,
        }

    def migrate(params: dict[str, Any]) -> dict[str, Any]:
        url = params.get("db_url", cfg.db_url)
        engine = init_schema(url)
        return {"status": "ok", "created_tables": sorted(engine.table_names())}

    def shutdown(_: dict[str, Any]) -> dict[str, Any]:
        server.stop()
        return {"status": "stopping"}

    server.register("health", health)
    server.register("db.migrate", migrate)
    server.register("shutdown", shutdown)
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aisounder-engine")
    parser.add_argument("--db-url", default="sqlite:///aisounder.db")
    parser.add_argument("--output-device", type=int, default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    cfg = EngineConfig(
        db_url=args.db_url,
        output_device_id=args.output_device,
    )
    server = _build_server(cfg)
    try:
        server.run(stdin=sys.stdin, stdout=sys.stdout)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
