from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Protocol


class DraftTrackGenerationError(RuntimeError):
    """An available provider failed while generating convenience-only drafts."""


@dataclass(frozen=True)
class DraftTrack:
    proposed_position: int | None
    proposed_title: str | None
    proposed_artist: str | None
    proposed_version_remaster_text: str | None
    source_keys: tuple[str, ...]
    ambiguity_flag: bool = False
    review_status: str = "UNREVIEWED"


@dataclass(frozen=True)
class DraftExtractionResult:
    available: bool
    provider: str
    message: str
    draft_tracks: tuple[DraftTrack, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "provider": self.provider,
            "message": self.message,
            "draft_tracks": [asdict(item) for item in self.draft_tracks],
        }


class DraftTrackProvider(Protocol):
    provider: str

    def available(self) -> bool:
        """Report whether this provider can generate draft tracks now."""

    def generate(self, source_keys: tuple[str, ...], supplied_text: str | None = None) -> DraftExtractionResult:
        """Return convenience-only draft rows; never governed evidence."""


class UnavailableTrackExtractionAdapter:
    provider = "automatic"

    def available(self) -> bool:
        return False

    def generate(self, source_keys: tuple[str, ...], supplied_text: str | None = None) -> DraftExtractionResult:
        raise RuntimeError("generate must not be called when the provider is unavailable")

    def unavailable_result(self) -> DraftExtractionResult:
        return DraftExtractionResult(
            available=False,
            provider=self.provider,
            message=(
                "No automatic extraction provider is configured. "
                "Paste a draft tracklist under Advanced tracklist tools, or install a provider later. "
                "No draft tracks have been created."
            ),
        )


class DelimitedTextTrackExtractionAdapter:
    """Mechanically split reviewer-supplied lines without interpreting them."""

    provider = "delimited_text"

    def available(self) -> bool:
        return True

    def generate(self, source_keys: tuple[str, ...], supplied_text: str | None = None) -> DraftExtractionResult:
        if supplied_text is None or not supplied_text.strip():
            raise ValueError("delimited text extraction requires supplied text")
        rows = []
        for line_number, line in enumerate(supplied_text.splitlines(), start=1):
            if not line.strip():
                continue
            fields = [field.strip() or None for field in line.split("|")]
            if len(fields) > 4:
                raise ValueError(f"line {line_number} has more than four delimited fields")
            fields.extend([None] * (4 - len(fields)))
            position_text, title, artist, version = fields
            position = None
            if position_text is not None:
                if not position_text.isdigit() or int(position_text) < 1:
                    raise ValueError(f"line {line_number} position must be a positive integer or blank")
                position = int(position_text)
            if title is None and artist is None and version is None:
                raise ValueError(f"line {line_number} contains no draft track text")
            rows.append(DraftTrack(
                proposed_position=position,
                proposed_title=title,
                proposed_artist=artist,
                proposed_version_remaster_text=version,
                source_keys=source_keys,
            ))
        return DraftExtractionResult(
            available=True,
            provider=self.provider,
            message=f"Created {len(rows)} unreviewed draft rows from supplied text.",
            draft_tracks=tuple(rows),
        )


class StructuredJsonDraftTrackProvider:
    """Strictly map external structured drafts into non-authoritative draft rows."""

    provider = "structured_json"

    def available(self) -> bool:
        return True

    def generate(self, source_keys: tuple[str, ...], supplied_text: str | None = None) -> DraftExtractionResult:
        if supplied_text is None or not supplied_text.strip():
            raise ValueError("structured draft import requires JSON text")
        try:
            document = json.loads(supplied_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON: {exc.msg}") from exc
        if not isinstance(document, dict) or set(document) != {"tracks"}:
            raise ValueError("expected an object containing only a tracks array")
        tracks = document["tracks"]
        if not isinstance(tracks, list):
            raise ValueError("expected tracks to be an array")
        allowed_sources = set(source_keys)
        rows = []
        allowed_fields = {"position", "title", "artist", "version", "uncertain", "source_keys"}
        for index, item in enumerate(tracks, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"at track {index}: expected an object")
            unknown = set(item) - allowed_fields
            if unknown:
                raise ValueError(f"at track {index}: unsupported fields: {sorted(unknown)}")
            position = item.get("position")
            if position is not None and (isinstance(position, bool) or not isinstance(position, int) or position < 1):
                raise ValueError(f"at track {index}: position must be a positive integer or null")
            title = _optional_exact_string(item, "title", index)
            artist = _optional_exact_string(item, "artist", index)
            version = _optional_exact_string(item, "version", index)
            if title is None and artist is None and version is None:
                raise ValueError(f"at track {index}: title, artist, or version is required")
            uncertain = item.get("uncertain", False)
            if not isinstance(uncertain, bool):
                raise ValueError(f"at track {index}: uncertain must be true or false")
            declared_sources = item.get("source_keys", [])
            if not isinstance(declared_sources, list) or not all(isinstance(key, str) and key for key in declared_sources):
                raise ValueError(f"at track {index}: source_keys must be an array of source keys")
            if len(declared_sources) != len(set(declared_sources)):
                raise ValueError(f"at track {index}: source_keys must not contain duplicates")
            unknown_sources = set(declared_sources) - allowed_sources
            if unknown_sources:
                raise ValueError(f"at track {index}: unknown staged sources: {sorted(unknown_sources)}")
            rows.append(DraftTrack(
                proposed_position=position,
                proposed_title=title,
                proposed_artist=artist,
                proposed_version_remaster_text=version,
                source_keys=tuple(declared_sources),
                ambiguity_flag=uncertain,
            ))
        return DraftExtractionResult(
            available=True,
            provider=self.provider,
            message=f"Imported {len(rows)} draft track{'s' if len(rows) != 1 else ''}. Review the list before confirmation.",
            draft_tracks=tuple(rows),
        )


def draft_track_provider(provider: str) -> DraftTrackProvider:
    if provider == UnavailableTrackExtractionAdapter.provider:
        return UnavailableTrackExtractionAdapter()
    if provider == DelimitedTextTrackExtractionAdapter.provider:
        return DelimitedTextTrackExtractionAdapter()
    if provider == StructuredJsonDraftTrackProvider.provider:
        return StructuredJsonDraftTrackProvider()
    raise ValueError(f"unsupported track extraction provider: {provider}")


def generate_draft_tracks(
    provider: DraftTrackProvider,
    source_keys: tuple[str, ...],
    supplied_text: str | None = None,
) -> DraftExtractionResult:
    if not provider.available():
        unavailable_result = getattr(provider, "unavailable_result", None)
        if unavailable_result is None:
            return DraftExtractionResult(
                available=False,
                provider=provider.provider,
                message="This draft-track provider is unavailable. No draft tracks have been created.",
            )
        return unavailable_result()
    try:
        return provider.generate(source_keys, supplied_text)
    except ValueError:
        raise
    except Exception as exc:
        raise DraftTrackGenerationError(f"draft-track provider failed: {exc}") from exc


def _optional_exact_string(item: dict[str, object], field: str, index: int) -> str | None:
    value = item.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or value == "":
        raise ValueError(f"at track {index}: {field} must be non-empty text or null")
    return value
