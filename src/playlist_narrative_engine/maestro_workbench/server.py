from __future__ import annotations

import argparse
import json
import mimetypes
import secrets
import socket
from dataclasses import dataclass
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
from playlist_narrative_engine.maestro_workbench.track_extraction import (
    DraftTrackGenerationError,
    draft_track_provider,
    generate_draft_tracks,
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
        try:
            self._require_access()
        except PermissionError as exc:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": str(exc)})
            return
        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        static_file = self._resolve_static_file(path)
        if static_file is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = static_file.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", _content_type_for(static_file))
        self.send_header("Content-Length", str(len(content)))
        self._send_no_cache_headers()
        supplied_query = self._query_access_token()
        if self.server.access_token is not None and supplied_query is not None:
            self.send_header("Set-Cookie", f"pne_workbench_token={supplied_query}; Path=/; HttpOnly; SameSite=Strict")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            self._require_access()
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
            elif path == "/api/generate-draft-tracklist":
                request = self._read_json()
                provider = _required_text(request, "provider")
                source_keys = request.get("source_keys", [])
                if not isinstance(source_keys, list) or not all(isinstance(item, str) for item in source_keys):
                    raise ValueError("source_keys must be a list of exact staged-source keys")
                supplied_text = request.get("supplied_text")
                if supplied_text is not None and not isinstance(supplied_text, str):
                    raise ValueError("supplied_text must be text when supplied")
                selected_provider = draft_track_provider(provider)
                extracted = generate_draft_tracks(selected_provider, tuple(source_keys), supplied_text)
                self._send_json(HTTPStatus.OK, extracted.to_dict())
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except PermissionError as exc:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": str(exc)})
        except DraftTrackGenerationError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _require_access(self) -> None:
        expected = self.server.access_token
        if expected is None:
            return
        supplied = self.headers.get("X-Workbench-Token") or self._query_access_token() or self._cookie_access_token() or ""
        if not secrets.compare_digest(supplied, expected):
            raise PermissionError("valid workbench session token required")

    def _query_access_token(self) -> str | None:
        from urllib.parse import parse_qs

        values = parse_qs(urlparse(self.path).query)
        supplied = values.get("session") or values.get("token")
        return supplied[0] if supplied else None

    def _cookie_access_token(self) -> str | None:
        for item in self.headers.get("Cookie", "").split(";"):
            name, separator, value = item.strip().partition("=")
            if separator and name == "pne_workbench_token":
                return value
        return None

    def _execute(self, operation: str, request: dict[str, Any]) -> dict[str, object]:
        kind = _required_text(request, "kind")
        with open_research_store_service(self.server.database_url) as service:
            operations = WorkbenchOperations(service)
            if operation == "validate":
                return operations.validate(kind, request.get("proposal"))
            return operations.ingest(kind, request.get("proposal"))

    def _resolve_static_file(self, path: str) -> Path | None:
        relative = "index.html" if path == "/" else path.lstrip("/")
        if not relative:
            return None
        candidate = (STATIC_ROOT / relative).resolve()
        try:
            candidate.relative_to(STATIC_ROOT.resolve())
        except ValueError:
            return None
        if not candidate.is_file():
            return None
        if candidate.suffix not in {".html", ".js", ".css"}:
            return None
        return candidate

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
        self._send_no_cache_headers()
        self.end_headers()
        self.wfile.write(content)

    def _send_no_cache_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")

    def log_message(self, format: str, *args: object) -> None:
        return


def _content_type_for(path: Path) -> str:
    if path.suffix == ".js":
        return "text/javascript; charset=utf-8"
    if path.suffix == ".css":
        return "text/css; charset=utf-8"
    if path.suffix == ".html":
        return "text/html; charset=utf-8"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


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
        help="Listen without authentication on a trusted local network",
    )
    parser.add_argument(
        "--secure",
        action="store_true",
        help="Require a fresh session token for LAN access (requires --lan)",
    )
    return parser


@dataclass(frozen=True)
class WorkbenchLaunchMode:
    name: str
    bind_host: str
    access_token: str | None


def resolve_launch_mode(*, lan: bool, secure: bool) -> WorkbenchLaunchMode:
    if secure and not lan:
        raise ValueError("--secure requires --lan")
    if not lan:
        return WorkbenchLaunchMode("localhost", "127.0.0.1", None)
    if not secure:
        return WorkbenchLaunchMode("trusted LAN", "0.0.0.0", None)
    return WorkbenchLaunchMode("protected LAN", "0.0.0.0", secrets.token_urlsafe(24))


def startup_lines(mode: WorkbenchLaunchMode, port: int, addresses: list[str]) -> list[str]:
    lines = ["Maestro Evidence Workbench", f"Mode: {mode.name}"]
    if mode.name == "localhost":
        return lines + [f"Open: http://127.0.0.1:{port}"]
    if mode.name == "trusted LAN":
        lines += [
            "WARNING: Trusted LAN mode enabled.",
            "This workbench is accessible to devices on your local network.",
            "Use only on networks you trust.",
            "Open:",
        ]
        return lines + [f"http://{address}:{port}" for address in addresses]
    lines += ["Session token generated for this launch.", "Open:"]
    return lines + [f"http://{address}:{port}/?session={mode.access_token}" for address in addresses]


def _local_ipv4_addresses() -> list[str]:
    addresses = {
        item[4][0]
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        if not item[4][0].startswith("127.")
    }
    return sorted(addresses) or ["127.0.0.1"]


def main() -> None:
    args = build_parser().parse_args()
    try:
        mode = resolve_launch_mode(lan=args.lan, secure=args.secure)
    except ValueError as exc:
        build_parser().error(str(exc))
    initialize_research_store(args.database_url)
    server = MaestroWorkbenchServer(
        (mode.bind_host, args.port),
        database_url=args.database_url,
        staging_root=args.staging_root,
        access_token=mode.access_token,
    )
    addresses = _local_ipv4_addresses() if args.lan else ["127.0.0.1"]
    for line in startup_lines(mode, server.server_port, addresses):
        print(line)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
