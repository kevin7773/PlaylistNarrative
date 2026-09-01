from __future__ import annotations

import re
import urllib.parse
import xml.parsers.expat
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import (
    FrozenModel,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.schemas import (
    PennyLocalITunesXMLFileSelectionEvidence,
)


class ITunesWindowsXMLProfileError(ValueError):
    pass


class XMLSafetyError(ITunesWindowsXMLProfileError):
    pass


class PlistStructureError(ITunesWindowsXMLProfileError):
    pass


class FrozenSourceProfileError(ITunesWindowsXMLProfileError):
    pass


@dataclass
class _XMLNode:
    name: str
    attributes: dict[str, str]
    children: list[_XMLNode] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    canonical_empty_element: bool = False

    @property
    def text(self) -> str:
        return "".join(self.text_parts)


class ProfileTrack(FrozenModel):
    track_id_correspondence: int
    persistent_id: str
    name: str
    artist: str
    total_time_milliseconds: int
    location: str


class VerifiedITunesWindowsXMLProfile(FrozenModel):
    library_persistent_id: str
    playlist_persistent_id: str
    tracks_by_correspondence_id: dict[int, ProfileTrack]
    playlist_track_ids: tuple[int, ...]


_XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'
_DOCTYPE = (
    '<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" '
    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">'
)
_UTC_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
_HEX_16 = re.compile(r"^[0-9A-F]{16}$")
_POSITIVE_KEY = re.compile(r"^[1-9][0-9]*$")
_PERCENT = re.compile(r"%(?![0-9A-Fa-f]{2})")
_ENTITY = re.compile(r"&([^;]+);")
_ALLOWED_ENTITIES = {"amp", "lt", "gt", "apos", "quot"}
_ALLOWED_ELEMENTS = {"plist", "dict", "array", "key", "string", "integer", "date", "true"}

_TOP_FIELDS = {
    "Major Version",
    "Minor Version",
    "Date",
    "Application Version",
    "Features",
    "Show Content Ratings",
    "Music Folder",
    "Library Persistent ID",
    "Tracks",
    "Playlists",
}
_PLAYLIST_FIELDS = {
    "Name",
    "Description",
    "Playlist ID",
    "Playlist Persistent ID",
    "All Items",
    "Playlist Items",
}
_TRACK_REQUIRED = {
    "Track ID",
    "Name",
    "Artist",
    "Album",
    "Genre",
    "Kind",
    "Size",
    "Total Time",
    "Track Number",
    "Year",
    "Date Modified",
    "Date Added",
    "Bit Rate",
    "Sample Rate",
    "Comments",
    "Sort Artist",
    "Persistent ID",
    "Track Type",
    "Location",
    "File Folder Count",
    "Library Folder Count",
}
_TRACK_OPTIONAL = {"Sort Album", "Sort Name"}


def verify_frozen_itunes_windows_xml_profile(
    evidence: PennyLocalITunesXMLFileSelectionEvidence,
) -> VerifiedITunesWindowsXMLProfile:
    if not isinstance(evidence, PennyLocalITunesXMLFileSelectionEvidence):
        raise FrozenSourceProfileError("profile verification requires selection evidence")
    receipt = evidence.source_receipt
    if len(receipt.items) != 1 or receipt.items[0].item_id != "item-000001":
        raise FrozenSourceProfileError("profile requires one exact receipt item")
    root = _parse_xml_safely(receipt.items[0].payload)
    return _verify_plist_profile(root)


def _parse_xml_safely(payload: bytes) -> _XMLNode:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise XMLSafetyError("UTF-8 BOM is forbidden")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise XMLSafetyError("XML must be strict UTF-8") from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if len(lines) < 3 or lines[0] != _XML_DECLARATION or lines[1] != _DOCTYPE:
        raise XMLSafetyError("XML declaration and inert external DOCTYPE must be exact")
    if normalized.count(_DOCTYPE) != 1:
        raise XMLSafetyError("DOCTYPE must occur exactly once")
    remainder = "\n".join(lines[2:])
    forbidden = ("<!DOCTYPE", "<!ENTITY", "<![", "<?", "<!--", "<xi:", "xsi:")
    if any(token in remainder for token in forbidden):
        raise XMLSafetyError("unsupported XML construct")
    if any(match.group(1) not in _ALLOWED_ENTITIES for match in _ENTITY.finditer(text)):
        raise XMLSafetyError("unsupported entity reference")

    parser = xml.parsers.expat.ParserCreate("UTF-8")
    parser.SetParamEntityParsing(xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER)
    stack: list[_XMLNode] = []
    roots: list[_XMLNode] = []
    doctype_seen = False

    def start(name: str, attributes: dict[str, str]) -> None:
        if name not in _ALLOWED_ELEMENTS:
            raise XMLSafetyError("unsupported XML element")
        node = _XMLNode(
            name=name,
            attributes=dict(attributes),
            canonical_empty_element=(
                name == "true" and payload.startswith(b"<true/>", parser.CurrentByteIndex)
            ),
        )
        if stack:
            stack[-1].children.append(node)
        else:
            roots.append(node)
        stack.append(node)

    def end(name: str) -> None:
        if not stack or stack[-1].name != name:
            raise XMLSafetyError("malformed XML element nesting")
        stack.pop()

    def chars(value: str) -> None:
        if stack:
            stack[-1].text_parts.append(value)
        elif value.strip():
            raise XMLSafetyError("non-whitespace content outside plist root")

    def doctype(name: str, system_id: str, public_id: str, internal: int) -> None:
        nonlocal doctype_seen
        if (
            doctype_seen
            or name != "plist"
            or public_id != "-//Apple Computer//DTD PLIST 1.0//EN"
            or system_id != "http://www.apple.com/DTDs/PropertyList-1.0.dtd"
            or internal
        ):
            raise XMLSafetyError("DOCTYPE is not the exact inert profile identifier")
        doctype_seen = True

    def reject(*_: object) -> int:
        raise XMLSafetyError("external or declared entity processing is forbidden")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = chars
    parser.StartDoctypeDeclHandler = doctype
    parser.EntityDeclHandler = reject
    parser.ExternalEntityRefHandler = reject
    parser.ProcessingInstructionHandler = reject
    parser.CommentHandler = reject
    try:
        parser.Parse(payload, True)
    except (xml.parsers.expat.ExpatError, XMLSafetyError) as exc:
        if isinstance(exc, XMLSafetyError):
            raise
        raise XMLSafetyError("malformed or unsafe XML") from exc
    if not doctype_seen or len(roots) != 1 or stack:
        raise XMLSafetyError("XML must contain one complete plist root")
    return roots[0]


def _verify_plist_profile(root: _XMLNode) -> VerifiedITunesWindowsXMLProfile:
    if root.name != "plist" or root.attributes != {"version": "1.0"}:
        raise PlistStructureError("plist 1.0 envelope is required")
    _require_container_content(root, "plist")
    if len(root.children) != 1 or root.children[0].name != "dict":
        raise PlistStructureError("plist must contain exactly one dictionary")
    top = _dict(root.children[0])
    _exact_keys(top, _TOP_FIELDS, "top-level")
    _integer(top, "Major Version", exact=1)
    _integer(top, "Minor Version", exact=1)
    _utc_date(top, "Date")
    if _scalar(top, "Application Version", "string") != "12.13.10.3":
        raise FrozenSourceProfileError("unsupported iTunes application version")
    _integer(top, "Features", exact=5)
    _true(top, "Show Content Ratings")
    _file_uri(_scalar(top, "Music Folder", "string"))
    library_id = _scalar(top, "Library Persistent ID", "string", pattern=_HEX_16)

    tracks_node = _typed(top, "Tracks", "dict")
    track_pairs = _dict(tracks_node)
    if not track_pairs:
        raise FrozenSourceProfileError("track dictionary must be nonempty")
    parsed_tracks: dict[int, ProfileTrack] = {}
    persistent_ids: set[str] = set()
    for dictionary_key, track_node in track_pairs.items():
        if not _POSITIVE_KEY.fullmatch(dictionary_key) or track_node.name != "dict":
            raise FrozenSourceProfileError("track dictionary key must be canonical positive integer")
        track = _track(dictionary_key, _dict(track_node))
        if track.persistent_id in persistent_ids:
            raise FrozenSourceProfileError("track persistent identities must be unique")
        persistent_ids.add(track.persistent_id)
        parsed_tracks[track.track_id_correspondence] = track

    playlists = _typed(top, "Playlists", "array")
    _require_container_content(playlists, "Playlists")
    if len(playlists.children) != 1 or playlists.children[0].name != "dict":
        raise FrozenSourceProfileError("exactly one ordinary playlist is required")
    playlist = _dict(playlists.children[0])
    _exact_keys(playlist, _PLAYLIST_FIELDS, "playlist")
    _scalar(playlist, "Name", "string", nonblank=True)
    _scalar(playlist, "Description", "string")
    _integer(playlist, "Playlist ID", positive=True)
    playlist_id = _scalar(
        playlist, "Playlist Persistent ID", "string", pattern=_HEX_16
    )
    _true(playlist, "All Items")
    items = _typed(playlist, "Playlist Items", "array")
    _require_container_content(items, "Playlist Items")
    references: list[int] = []
    for child in items.children:
        if child.name != "dict":
            raise PlistStructureError("playlist item must be a dictionary")
        pair = _dict(child)
        _exact_keys(pair, {"Track ID"}, "playlist item")
        reference = _integer(pair, "Track ID", positive=True)
        if reference not in parsed_tracks:
            raise FrozenSourceProfileError("dangling playlist Track ID")
        references.append(reference)
    if len(references) != len(set(references)):
        raise FrozenSourceProfileError("duplicate playlist membership is forbidden")
    if set(references) != set(parsed_tracks):
        raise FrozenSourceProfileError("playlist must represent every top-level track exactly once")
    return VerifiedITunesWindowsXMLProfile(
        library_persistent_id=library_id,
        playlist_persistent_id=playlist_id,
        tracks_by_correspondence_id=parsed_tracks,
        playlist_track_ids=tuple(references),
    )


def _track(dictionary_key: str, values: dict[str, _XMLNode]) -> ProfileTrack:
    _exact_keys(values, _TRACK_REQUIRED, "track", optional=_TRACK_OPTIONAL)
    track_id = _integer(values, "Track ID", positive=True)
    if str(track_id) != dictionary_key:
        raise FrozenSourceProfileError("Track ID must match its dictionary key")
    for name in ("Name", "Artist", "Album", "Genre", "Comments", "Sort Artist"):
        _scalar(values, name, "string", nonblank=True)
    for name in _TRACK_OPTIONAL:
        if name in values:
            _scalar(values, name, "string", nonblank=True)
    if _scalar(values, "Kind", "string") != "MPEG audio file":
        raise FrozenSourceProfileError("unsupported media Kind")
    if _scalar(values, "Track Type", "string") != "File":
        raise FrozenSourceProfileError("unsupported Track Type")
    for name in ("Size", "Total Time", "Track Number", "Year", "Bit Rate", "Sample Rate"):
        _integer(values, name, positive=True)
    _integer(values, "File Folder Count", exact=-1)
    _integer(values, "Library Folder Count", exact=-1)
    for name in ("Date Modified", "Date Added"):
        _utc_date(values, name)
    persistent_id = _scalar(values, "Persistent ID", "string", pattern=_HEX_16)
    location = _scalar(values, "Location", "string")
    _file_uri(location)
    return ProfileTrack(
        track_id_correspondence=track_id,
        persistent_id=persistent_id,
        name=_scalar(values, "Name", "string", nonblank=True),
        artist=_scalar(values, "Artist", "string", nonblank=True),
        total_time_milliseconds=_integer(values, "Total Time", positive=True),
        location=location,
    )


def _dict(node: _XMLNode) -> dict[str, _XMLNode]:
    if node.name != "dict" or node.attributes:
        raise PlistStructureError("plist dictionary must alternate exact key/value elements")
    _require_container_content(node, "plist dictionary")
    if len(node.children) % 2:
        raise PlistStructureError("plist dictionary must alternate exact key/value elements")
    result: dict[str, _XMLNode] = {}
    for index in range(0, len(node.children), 2):
        key_node, value = node.children[index : index + 2]
        if key_node.name != "key" or key_node.attributes or key_node.children:
            raise PlistStructureError("plist dictionary key position is invalid")
        key = key_node.text
        if key in result:
            raise PlistStructureError(f"duplicate plist key: {key}")
        result[key] = value
    return result


def _exact_keys(
    values: dict[str, _XMLNode],
    required: set[str],
    scope: str,
    *,
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    if not required.issubset(values) or not set(values).issubset(required | optional):
        raise FrozenSourceProfileError(f"{scope} fields do not match the frozen profile")


def _typed(values: dict[str, _XMLNode], key: str, kind: str) -> _XMLNode:
    node = values[key]
    if node.name != kind or node.attributes:
        raise PlistStructureError(f"{key} must be plist {kind}")
    return node


def _scalar(
    values: dict[str, _XMLNode],
    key: str,
    kind: str,
    *,
    nonblank: bool = False,
    pattern: re.Pattern[str] | None = None,
) -> str:
    node = _typed(values, key, kind)
    if (
        node.children
        or (nonblank and not node.text.strip())
        or (pattern and not pattern.fullmatch(node.text))
    ):
        raise FrozenSourceProfileError(f"{key} value is outside the frozen profile")
    return node.text


def _utc_date(values: dict[str, _XMLNode], key: str) -> str:
    value = _scalar(values, key, "date", nonblank=True, pattern=_UTC_DATE)
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise FrozenSourceProfileError(
            f"{key} value is outside the frozen profile"
        ) from exc
    return value


def _integer(
    values: dict[str, _XMLNode],
    key: str,
    *,
    positive: bool = False,
    exact: int | None = None,
) -> int:
    raw = _scalar(values, key, "integer")
    if not re.fullmatch(r"-?(0|[1-9][0-9]*)", raw):
        raise PlistStructureError(f"{key} integer is not canonical")
    value = int(raw)
    if (positive and value <= 0) or (exact is not None and value != exact):
        raise FrozenSourceProfileError(f"{key} integer is outside the frozen profile")
    return value


def _true(values: dict[str, _XMLNode], key: str) -> None:
    node = _typed(values, key, "true")
    if node.children or node.text or not node.canonical_empty_element:
        raise PlistStructureError(f"{key} true value must use canonical empty form")


def _require_container_content(node: _XMLNode, scope: str) -> None:
    if node.text.strip():
        raise PlistStructureError(
            f"{scope} must contain only plist child elements and formatting whitespace"
        )


def _file_uri(value: str) -> None:
    if _PERCENT.search(value) or "\\" in value:
        raise FrozenSourceProfileError("file URI is malformed")
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme != "file"
        or parsed.netloc != "localhost"
        or parsed.query
        or parsed.fragment
        or not re.match(r"^/[A-Za-z]:/", parsed.path)
    ):
        raise FrozenSourceProfileError("file URI is not absolute file://localhost Windows form")
    try:
        decoded = urllib.parse.unquote_to_bytes(parsed.path).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise FrozenSourceProfileError("file URI percent encoding is not strict UTF-8") from exc
    if any(segment in {".", ".."} for segment in decoded.split("/")):
        raise FrozenSourceProfileError("relative file URI segments are forbidden")
