from __future__ import annotations

import argparse
import json
import secrets
import socket
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from playlist_narrative_engine.maestro_workbench.operations import (
    EvidenceStager,
    WorkbenchOperations,
)
from playlist_narrative_engine.maestro_workbench.proposal_builder import (
    build_governed_proposal,
)
from playlist_narrative_engine.research_store.service import (
    initialize_research_store,
    open_research_store_service,
)


MAX_JSON_BYTES = 5 * 1024 * 1024
MAX_EVIDENCE_BYTES = 50 * 1024 * 1024
STATIC_ROOT = Path(__file__).with_name("static")


class MaestroWorkbenchServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        *,
        database_url: str | None = None,
        staging_root: Path | None = None,
        access_token: str | None = None,
    ) -> None:
        super().__init__(address, MaestroWorkbenchHandler)
        self.database_url = database_url
        self.evidence_stager = EvidenceStager(staging_root)
        self.access_token = access_token


class MaestroWorkbenchHandler(BaseHTTPRequestHandler):
    server: MaestroWorkbenchServer

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            try:
                self._require_api_access()
            except PermissionError as exc:
                self._send_json(HTTPStatus.FORBIDDEN, {"error": str(exc)})
                return
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        static_files = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
        }
        selected = static_files.get(path)
        if selected is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        filename, content_type = selected
        content = (STATIC_ROOT / filename).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            self._require_api_access()
            if path == "/api/stage-evidence":
                self._stage_evidence()
            elif path == "/api/validate":
                request = self._read_json()
                self._send_json(HTTPStatus.OK, self._execute("validate", request))
            elif path == "/api/ingest":
                request = self._read_json()
                self._send_json(HTTPStatus.CREATED, self._execute("ingest", request))
            elif path == "/api/build-proposal":
                request = self._read_json()
                declarations = request.get("declarations")
                staged_evidence = request.get("staged_evidence")
                if not isinstance(declarations, dict) or not isinstance(staged_evidence, list):
                    raise ValueError("declarations and staged_evidence are required")
                self._send_json(HTTPStatus.OK, {
                    "proposal": build_governed_proposal(
                        _required_text(request, "kind"), declarations, staged_evidence
                    )
                })
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except PermissionError as exc:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": str(exc)})
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _require_api_access(self) -> None:
        expected = self.server.access_token
        if expected is None:
            return
        supplied = self.headers.get("X-Workbench-Token", "")
        if not secrets.compare_digest(supplied, expected):
            raise PermissionError("valid workbench session token required")

    def _execute(self, operation: str, request: dict[str, Any]) -> dict[str, object]:
        kind = _required_text(request, "kind")
        with open_research_store_service(self.server.database_url) as service:
            operations = WorkbenchOperations(service)
            if operation == "validate":
                return operations.validate(kind, request.get("proposal"))
            return operations.ingest(kind, request.get("proposal"))

    def _stage_evidence(self) -> None:
        filename = self.headers.get("X-Original-Filename")
        if filename is None:
            raise ValueError("X-Original-Filename is required")
        content = self._read_body(MAX_EVIDENCE_BYTES)
        staged = self.server.evidence_stager.stage(unquote(filename), content)
        self._send_json(HTTPStatus.CREATED, {
            "original_filename": staged.original_filename,
            "local_path": staged.local_path,
            "sha256": staged.sha256,
            "size_bytes": staged.size_bytes,
        })

    def _read_json(self) -> dict[str, Any]:
        document = json.loads(self._read_body(MAX_JSON_BYTES).decode("utf-8"))
        if not isinstance(document, dict):
            raise ValueError("request body must be a JSON object")
        return document

    def _read_body(self, maximum: int) -> bytes:
        value = self.headers.get("Content-Length")
        if value is None:
            raise ValueError("Content-Length is required")
        length = int(value)
        if length < 0 or length > maximum:
            raise ValueError("request body exceeds the permitted size")
        return self.rfile.read(length)

    def _send_json(self, status: HTTPStatus, document: object) -> None:
        content = json.dumps(document, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: object) -> None:
        return


def _required_text(document: dict[str, Any], field: str) -> str:
    value = document.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} is required")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pne-maestro-workbench")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--database-url")
    parser.add_argument("--staging-root", type=Path)
    parser.add_argument(
        "--lan",
        action="store_true",
        help="Listen on the local network with a random API access token",
    )
    return parser


def _local_ipv4_addresses() -> list[str]:
    addresses = {
        item[4][0]
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        if not item[4][0].startswith("127.")
    }
    return sorted(addresses) or ["127.0.0.1"]


def main() -> None:
    args = build_parser().parse_args()
    initialize_research_store(args.database_url)
    access_token = secrets.token_urlsafe(24) if args.lan else None
    bind_host = "0.0.0.0" if args.lan else "127.0.0.1"
    server = MaestroWorkbenchServer(
        (bind_host, args.port),
        database_url=args.database_url,
        staging_root=args.staging_root,
        access_token=access_token,
    )
    if args.lan:
        print("Maestro Workbench LAN access is enabled for this session.")
        for address in _local_ipv4_addresses():
            print(f"  http://{address}:{server.server_port}/?token={access_token}")
        print("Keep this tokenized URL private. Press Ctrl+C to stop LAN access.")
    else:
        print(f"Maestro Workbench listening at http://127.0.0.1:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
