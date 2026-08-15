from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import mimetypes
import os
import secrets
import socket
import sys
from urllib.parse import quote
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
from playlist_narrative_engine.maestro_workbench.screenshot_extraction import (
    RapidOCRScreenshotExtractor,
    ScreenshotExtractor,
    extract_screenshot_draft,
    maestro_layout_profile,
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
from playlist_narrative_engine.research_store.migrations import CURRENT_SCHEMA_VERSION
from playlist_narrative_engine.research_store.study_schemas import StudyRegistrationInput
from playlist_narrative_engine.research_store.study_closeout import (
    closeout_json_bytes,
    closeout_markdown,
)


MAX_JSON_BYTES = 5 * 1024 * 1024
MAX_EVIDENCE_BYTES = 50 * 1024 * 1024
STATIC_ROOT = Path(__file__).with_name("static")
WORKBENCH_CONTRACT_CAPABILITIES = (
    "study.constraint.structured_evaluation_plan",
    "study.protocol.execution_contract",
)
WORKBENCH_API_CONTRACT_VERSION = "p8.1-runtime-identity-v1"


def workbench_runtime_identity(*, launch_mode: str = "unknown") -> dict[str, Any]:
    """Return explicit process/source/contract identity for split-version detection."""
    schema = StudyRegistrationInput.model_json_schema()
    canonical_schema = json.dumps(
        schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    asset_hasher = hashlib.sha256()
    asset_names = ("studies.html", "study_builder.js", "studies.js")
    for name in asset_names:
        asset_hasher.update(name.encode("utf-8"))
        asset_hasher.update(b"\0")
        asset_hasher.update((STATIC_ROOT / name).read_bytes())
        asset_hasher.update(b"\0")
    try:
        package_version = importlib.metadata.version("playlist-narrative-engine")
    except importlib.metadata.PackageNotFoundError:
        package_version = "source-tree"
    return {
        "identity_version": 1,
        "api_contract_version": WORKBENCH_API_CONTRACT_VERSION,
        "package_version": package_version,
        "process_id": os.getpid(),
        "python_executable": str(Path(sys.executable).resolve()),
        "backend_module": str(Path(__file__).resolve()),
        "static_root": str(STATIC_ROOT.resolve()),
        "launch_mode": launch_mode,
        "research_schema_version": CURRENT_SCHEMA_VERSION,
        "study_contract_sha256": hashlib.sha256(canonical_schema).hexdigest(),
        "study_contract_capabilities": list(WORKBENCH_CONTRACT_CAPABILITIES),
        "studies_assets_sha256": asset_hasher.hexdigest(),
        "studies_assets": list(asset_names),
    }


class MaestroWorkbenchServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        *,
        database_url: str | None = None,
        staging_root: Path | None = None,
        access_token: str | None = None,
        launch_mode: str = "unknown",
        screenshot_extractor: ScreenshotExtractor | None = None,
    ) -> None:
        super().__init__(address, MaestroWorkbenchHandler)
        self.database_url = database_url
        self.evidence_stager = EvidenceStager(staging_root)
        self.access_token = access_token
        self.launch_mode = launch_mode
        self.screenshot_extractor = screenshot_extractor
        self.staged_paths: set[str] = set()


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
        if path == "/api/runtime-identity":
            self._send_json(
                HTTPStatus.OK,
                workbench_runtime_identity(launch_mode=self.server.launch_mode),
            )
            return
        if path == "/api/studies":
            self._send_json(HTTPStatus.OK, {"studies": self._study_operation("list")})
            return
        if path.startswith("/api/study-runs/"):
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[3] == "structured-evaluation":
                try:
                    result = self._study_operation("structured-run", int(parts[2]))
                    self._send_json(HTTPStatus.OK if result is not None else HTTPStatus.NOT_FOUND,
                                    result if result is not None else {"error": "structured run evaluation not found"})
                except ValueError as exc:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
        if path.startswith("/api/studies/"):
            parts = path.strip("/").split("/")
            try:
                study_id = int(parts[2])
                if len(parts) == 5 and parts[3] == "protocols":
                    result = self._study_operation("protocol", study_id, int(parts[4]))
                elif len(parts) == 5 and parts[3] == "evaluations":
                    result = self._study_operation("evaluation", study_id, int(parts[4]))
                elif len(parts) == 5 and parts[3] == "explorations":
                    result = self._study_operation("exploration", study_id, int(parts[4]))
                elif len(parts) == 5 and parts[3] == "closeouts":
                    result = self._study_operation("closeout", study_id, int(parts[4]))
                elif len(parts) == 6 and parts[3] == "closeouts":
                    result = self._study_operation("closeout", study_id, int(parts[4]))
                    if result is None:
                        self._send_json(HTTPStatus.NOT_FOUND, {"error": "study record not found"})
                        return
                    filename = f"{result['registered']['study_key']}-v{result['registered']['protocol_version']}-closeout"
                    if parts[5] == "report.json":
                        self._send_download(closeout_json_bytes(result), "application/json; charset=utf-8", filename + ".json")
                    elif parts[5] == "report.md":
                        self._send_download(closeout_markdown(result).encode("utf-8"), "text/markdown; charset=utf-8", filename + ".md")
                    else:
                        self.send_error(HTTPStatus.NOT_FOUND)
                    return
                elif len(parts) == 3:
                    result = self._study_operation("get", study_id)
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                if result is None:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "study record not found"})
                else:
                    self._send_json(HTTPStatus.OK, result)
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
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
            elif path == "/api/studies/validate":
                self._send_json(HTTPStatus.OK, self._study_operation("validate", self._read_json()))
            elif path == "/api/studies/register":
                self._send_json(HTTPStatus.CREATED, self._study_operation("register", self._read_json()))
            elif path.startswith("/api/study-runs/"):
                parts = path.strip("/").split("/")
                if len(parts) != 4:
                    raise ValueError("invalid planned-run operation")
                run_id = int(parts[2])
                request = self._read_json()
                if parts[3] == "operational-attempts":
                    result = self._study_operation("attempt", run_id, request)
                elif parts[3] == "failures":
                    result = self._study_operation(
                        "failure", run_id, _required_text(request, "disposition"), request.get("failure")
                    )
                elif parts[3] == "realize-experiment":
                    result = self._study_operation("realize", run_id, request.get("proposal"))
                elif parts[3] == "structured-worksheet":
                    result = self._study_operation("structured-worksheet", run_id, request.get("proposal"))
                elif parts[3] == "structured-preview":
                    result = self._study_operation(
                        "structured-preview", run_id, request.get("proposal"), request.get("structured_evaluation")
                    )
                elif parts[3] == "realize-structured-experiment":
                    result = self._study_operation(
                        "realize-structured", run_id, request.get("proposal"), request.get("structured_evaluation")
                    )
                else:
                    raise ValueError("invalid planned-run operation")
                response_status = (
                    HTTPStatus.OK
                    if parts[3] in {"structured-worksheet", "structured-preview"}
                    else HTTPStatus.CREATED
                )
                self._send_json(response_status, result)
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
            elif path == "/api/extract-screenshot-draft":
                request = self._read_json()
                staged_sources = request.get("staged_sources")
                if not isinstance(staged_sources, list) or not staged_sources:
                    raise ValueError("staged_sources must be a non-empty list")
                for source in staged_sources:
                    if not isinstance(source, dict):
                        raise ValueError("each staged source must be an object")
                    _required_text(source, "source_key")
                    local_path = _required_text(source, "local_path")
                    if str(Path(local_path).resolve()) not in self.server.staged_paths:
                        raise ValueError("screenshot extraction accepts only evidence staged by this Workbench launch")
                extractor = self.server.screenshot_extractor or RapidOCRScreenshotExtractor()
                try:
                    review = extract_screenshot_draft(extractor, staged_sources)
                except Exception as exc:
                    raise DraftTrackGenerationError(f"screenshot extraction failed: {exc}") from exc
                self._send_json(HTTPStatus.OK, review.to_dict())
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

    def _study_operation(self, operation: str, *args):
        with open_research_store_service(self.server.database_url) as service:
            operations = WorkbenchOperations(service)
            return {
                "list": operations.list_studies,
                "get": operations.get_study,
                "protocol": operations.get_protocol,
                "evaluation": operations.evaluate_study,
                "exploration": operations.explore_study,
                "closeout": operations.closeout_study,
                "validate": operations.validate_study,
                "register": operations.register_study,
                "attempt": operations.record_operational_attempt,
                "failure": operations.record_study_failure,
                "realize": operations.realize_study_experiment,
                "structured-worksheet": operations.prepare_structured_worksheet,
                "structured-preview": operations.preview_structured_evaluation,
                "realize-structured": operations.realize_structured_study_experiment,
                "structured-run": operations.get_structured_run_evaluation,
            }[operation](*args)

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
        self.server.staged_paths.add(str(Path(staged.local_path).resolve()))
        from PIL import Image

        try:
            with Image.open(staged.local_path) as image:
                width, height = image.size
        except Exception:
            width = height = None
        profile = maestro_layout_profile(width, height) if width is not None and height is not None else None
        self._send_json(HTTPStatus.CREATED, {
            "original_filename": staged.original_filename,
            "local_path": staged.local_path,
            "sha256": staged.sha256,
            "size_bytes": staged.size_bytes,
            "width": width,
            "height": height,
            "screenshot_extraction_supported": profile is not None,
            "screenshot_layout_profile": profile.name if profile else None,
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

    def _send_download(self, content: bytes, content_type: str, filename: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(filename)}")
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


def startup_lines(
    mode: WorkbenchLaunchMode,
    port: int,
    addresses: list[str],
    identity: dict[str, Any] | None = None,
) -> list[str]:
    identity = identity or workbench_runtime_identity(launch_mode=mode.name)
    lines = [
        "Maestro Evidence Workbench",
        f"Mode: {mode.name}",
        f"Process: {identity['process_id']}",
        f"Python: {identity['python_executable']}",
        f"Backend source: {identity['backend_module']}",
        f"Static source: {identity['static_root']}",
        f"Research schema: v{identity['research_schema_version']}",
        f"Workbench API contract: {identity['api_contract_version']}",
        f"Study contract: {identity['study_contract_sha256']}",
        f"Studies assets: {identity['studies_assets_sha256']}",
    ]
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
    try:
        server = MaestroWorkbenchServer(
            (mode.bind_host, args.port),
            database_url=args.database_url,
            staging_root=args.staging_root,
            access_token=mode.access_token,
            launch_mode=mode.name,
        )
    except OSError as exc:
        if getattr(exc, "winerror", None) == 10048 or exc.errno in {48, 98, 10048}:
            raise SystemExit(
                f"Cannot start Maestro Evidence Workbench: port {args.port} is already in use. "
                "Stop the existing listener or choose another --port; do not assume it is running this workspace."
            ) from exc
        raise
    addresses = _local_ipv4_addresses() if args.lan else ["127.0.0.1"]
    identity = workbench_runtime_identity(launch_mode=mode.name)
    for line in startup_lines(mode, server.server_port, addresses, identity):
        print(line)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
