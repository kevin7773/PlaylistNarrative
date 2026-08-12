from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from difflib import SequenceMatcher
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class MaestroLayoutProfile:
    name: str
    width: int
    height: int
    playlist_x_min: float
    playlist_x_max: float
    default_playlist_top: float
    row_gap: float
    right_edge_threshold: float
    lower_review_margin: float
    fixed_player_top: float | None = None
    header_marker_y: tuple[float, float] | None = None
    header_playlist_top: float | None = None
    title_region: tuple[float, float, float, float] | None = None
    description_region: tuple[float, float, float, float] | None = None


MAESTRO_590X1280 = MaestroLayoutProfile(
    name="maestro_590x1280", width=590, height=1280,
    playlist_x_min=0.18, playlist_x_max=0.35,
    default_playlist_top=0.06, row_gap=0.04,
    right_edge_threshold=0.88, lower_review_margin=0.10,
)
MAESTRO_1179X2556 = MaestroLayoutProfile(
    name="maestro_1179x2556", width=1179, height=2556,
    playlist_x_min=0.20, playlist_x_max=0.30,
    default_playlist_top=0.06, row_gap=0.04,
    right_edge_threshold=0.88, lower_review_margin=0.10,
    fixed_player_top=0.845,
    header_marker_y=(0.13, 0.19), header_playlist_top=0.34,
    title_region=(0.02, 0.12, 0.90, 0.19),
    description_region=(0.02, 0.19, 0.90, 0.27),
)
MAESTRO_LAYOUT_PROFILES = (MAESTRO_590X1280, MAESTRO_1179X2556)


def maestro_layout_profile(width: int, height: int) -> MaestroLayoutProfile | None:
    return next((profile for profile in MAESTRO_LAYOUT_PROFILES if (profile.width, profile.height) == (width, height)), None)


@dataclass(frozen=True)
class TextLine:
    text: str
    confidence: float
    x0: float
    x1: float
    y0: float
    y1: float


@dataclass(frozen=True)
class ScreenshotTrackObservation:
    proposed_position: int | None
    title: str | None
    artist: str | None
    source_keys: tuple[str, ...]
    ocr_confidence: float
    structural_status: str
    completeness_status: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScreenshotObservation:
    source_key: str
    supported: bool
    width: int
    height: int
    generated_title_candidates: tuple[str, ...] = ()
    generated_description_candidates: tuple[str, ...] = ()
    tracks: tuple[ScreenshotTrackObservation, ...] = ()
    playlist_start: str = "UNRESOLVED"
    playlist_end: str = "UNRESOLVED"
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScreenshotExtractionReview:
    observations: tuple[ScreenshotObservation, ...]
    draft_tracks: tuple[ScreenshotTrackObservation, ...]
    transitions: tuple[dict[str, object], ...]
    coverage: tuple[dict[str, object], ...] = ()
    generated_title: str | None = None
    generated_description: str | None = None
    continuity_established: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ScreenshotExtractor(Protocol):
    def extract(self, source_key: str, path: Path) -> ScreenshotObservation:
        """Create disposable observations for one exact staged source."""


class MaestroLayoutSegmenter:
    """Geometry-only segmentation selected by exact validated dimensions."""

    def segment(self, source_key: str, image, lines: list[TextLine]) -> ScreenshotObservation:
        height, width = image.shape[:2]
        profile = maestro_layout_profile(width, height)
        if profile is None:
            return ScreenshotObservation(
                source_key=source_key,
                supported=False,
                width=width,
                height=height,
                warnings=(f"Unsupported screenshot layout {width}x{height}; automatic extraction requires an exact validated Maestro layout.",),
            )

        bottom = self._player_boundary(image, profile)
        header_present = self._header_present(lines, profile)
        playlist_top = profile.header_playlist_top if header_present else profile.default_playlist_top
        playlist_lines = [
            line for line in lines
            if width * profile.playlist_x_min <= line.x0 <= width * profile.playlist_x_max
            and height * playlist_top <= line.y0
            and line.y1 < bottom
        ]
        groups: list[list[TextLine]] = []
        for line in sorted(playlist_lines, key=lambda item: (item.y0, item.x0)):
            if not groups or line.y0 - groups[-1][-1].y0 > height * profile.row_gap:
                groups.append([line])
            else:
                groups[-1].append(line)

        tracks = tuple(self._track(source_key, group, bottom, height, width, profile) for group in groups)
        if profile.title_region is None:
            header = [line.text for line in lines if line.y0 < (groups[0][0].y0 if groups else height * 0.35) and line.x0 < width * 0.18 and line.y0 > height * 0.06]
            titles, descriptions = tuple(header[:1]), tuple(header[1:])
        elif header_present:
            titles = tuple(line.text for line in lines if self._inside(line, width, height, profile.title_region))
            description_lines = [line.text for line in sorted(lines, key=lambda item: (item.y0, item.x0)) if self._inside(line, width, height, profile.description_region)]
            descriptions = (" ".join(description_lines),) if description_lines else ()
        else:
            titles, descriptions = (), ()
        return ScreenshotObservation(
            source_key=source_key,
            supported=True,
            width=width,
            height=height,
            generated_title_candidates=titles,
            generated_description_candidates=descriptions,
            tracks=tracks,
            warnings=(),
        )

    @staticmethod
    def _inside(line: TextLine, width: int, height: int, region: tuple[float, float, float, float] | None) -> bool:
        if region is None:
            return False
        x0, y0, x1, y1 = region
        return width * x0 <= line.x0 and line.x1 <= width * x1 and height * y0 <= line.y0 and line.y1 <= height * y1

    @staticmethod
    def _header_present(lines: list[TextLine], profile: MaestroLayoutProfile) -> bool:
        if profile.header_marker_y is None:
            return False
        start, end = profile.header_marker_y
        return any(
            line.x0 < profile.width * 0.10
            and profile.height * start <= line.y0 <= profile.height * end
            and line.y1 - line.y0 >= profile.height * 0.025
            for line in lines
        )

    @staticmethod
    def _player_boundary(image, profile: MaestroLayoutProfile) -> float:
        if profile.fixed_player_top is not None:
            return profile.height * profile.fixed_player_top
        import cv2

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        candidates = []
        for y in range(int(height * 0.70), int(height * 0.92)):
            if (gray[y] >= 185).sum() / width >= 0.88:
                candidates.append(y)
        return float(min(candidates) - 2) if candidates else height * 0.84

    @staticmethod
    def _track(source_key: str, group: list[TextLine], bottom: float, height: int, width: int, profile: MaestroLayoutProfile) -> ScreenshotTrackObservation:
        observations = tuple(line.text for line in group)
        confidence = min(line.confidence for line in group)
        ellipsis = any(line.text.rstrip().endswith(("...", "..", "…")) for line in group)
        edge_risk = max(line.x1 for line in group) >= width * profile.right_edge_threshold
        lower_risk = group[-1].y1 >= bottom - height * profile.lower_review_margin
        if len(group) == 1:
            structural = "STRUCTURALLY_AMBIGUOUS"
        elif len(group) > 2 or lower_risk:
            structural = "REVIEW_RECOMMENDED"
        else:
            structural = "STRUCTURALLY_CLEAR"
        if ellipsis:
            completeness = "TRUNCATED_IN_SOURCE"
        elif edge_risk or lower_risk:
            completeness = "POSSIBLY_CLIPPED"
        elif confidence < 0.995:
            completeness = "TEXT_AMBIGUOUS"
        else:
            completeness = "COMPLETE_AS_OBSERVED"
        warnings = []
        if structural != "STRUCTURALLY_CLEAR":
            warnings.append("Review title/artist row grouping.")
        if completeness != "COMPLETE_AS_OBSERVED":
            warnings.append("Review displayed text completeness.")
        return ScreenshotTrackObservation(
            proposed_position=None,
            title=" ".join(observations[:-1]) if len(group) > 1 else observations[0],
            artist=observations[-1] if len(group) > 1 else None,
            source_keys=(source_key,),
            ocr_confidence=confidence,
            structural_status=structural,
            completeness_status=completeness,
            warnings=tuple(warnings),
        )


Maestro590x1280Segmenter = MaestroLayoutSegmenter


class RapidOCRScreenshotExtractor:
    def __init__(self, *, engine=None, segmenter: MaestroLayoutSegmenter | None = None) -> None:
        self._engine = engine
        self._segmenter = segmenter or MaestroLayoutSegmenter()

    def extract(self, source_key: str, path: Path) -> ScreenshotObservation:
        from PIL import Image

        with Image.open(path) as image_file:
            width, height = image_file.size
        if maestro_layout_profile(width, height) is None:
            return ScreenshotObservation(
                source_key=source_key, supported=False, width=width, height=height,
                warnings=(f"Unsupported screenshot layout {width}x{height}; automatic extraction requires an exact validated Maestro layout.",),
            )
        engine = self._engine
        if engine is None:
            from rapidocr import RapidOCR

            engine = self._engine = RapidOCR()
        output = engine(str(path))
        lines = [] if output.boxes is None else [
            TextLine(
                text=str(text), confidence=float(confidence),
                x0=float(min(point[0] for point in box)), x1=float(max(point[0] for point in box)),
                y0=float(min(point[1] for point in box)), y1=float(max(point[1] for point in box)),
            )
            for box, text, confidence in zip(output.boxes, output.txts, output.scores)
        ]
        return self._segmenter.segment(source_key, output.img, lines)


class ScreenshotDraftReconciler:
    def reconcile(self, observations: tuple[ScreenshotObservation, ...]) -> ScreenshotExtractionReview:
        supported = [item for item in observations if item.supported]
        tracks: list[ScreenshotTrackObservation] = []
        transitions: list[dict[str, object]] = []
        for index, observation in enumerate(supported):
            current = list(observation.tracks)
            if index:
                prior = supported[index - 1]
                overlap = self._exact_overlap(list(prior.tracks), current)
                if overlap:
                    transitions.append({"status": "EXACT_OVERLAP_ACCEPTED", "source_keys": [prior.source_key, observation.source_key], "overlap_size": overlap})
                    for offset in range(overlap):
                        tracks[-overlap + offset] = replace(
                            tracks[-overlap + offset],
                            source_keys=(prior.source_key, observation.source_key),
                        )
                    current = current[overlap:]
                else:
                    self._mark_disagreement(tracks, current)
                    transitions.append({"status": "UNRESOLVED_CONTINUITY", "source_keys": [prior.source_key, observation.source_key], "overlap_size": 0})
            tracks.extend(current)
        positioned = tuple(replace(item, proposed_position=index) for index, item in enumerate(tracks, start=1))
        coverage = []
        for observation in supported:
            positions = [item.proposed_position for item in positioned if observation.source_key in item.source_keys]
            coverage.append({
                "source_key": observation.source_key,
                "start": min(positions) if positions else None,
                "end": max(positions) if positions else None,
                "playlist_start": observation.playlist_start,
                "playlist_end": observation.playlist_end,
            })
        titles = [value for item in supported for value in item.generated_title_candidates]
        descriptions = [value for item in supported for value in item.generated_description_candidates]
        return ScreenshotExtractionReview(
            observations=observations,
            draft_tracks=positioned,
            transitions=tuple(transitions),
            coverage=tuple(coverage),
            generated_title=titles[0] if len(titles) == 1 else None,
            generated_description=descriptions[0] if len(descriptions) == 1 else None,
            continuity_established=all(
                item["status"] != "UNRESOLVED_CONTINUITY" for item in transitions
            ),
        )

    @staticmethod
    def _exact_overlap(left: list[ScreenshotTrackObservation], right: list[ScreenshotTrackObservation]) -> int:
        for size in range(min(len(left), len(right)), 0, -1):
            left_pairs = [(item.title, item.artist) for item in left[-size:]]
            right_pairs = [(item.title, item.artist) for item in right[:size]]
            if all(title is not None and artist is not None for title, artist in left_pairs) and left_pairs == right_pairs:
                return size
        return 0

    @staticmethod
    def _mark_disagreement(left: list[ScreenshotTrackObservation], right: list[ScreenshotTrackObservation]) -> None:
        for left_index in range(max(0, len(left) - 2), len(left)):
            for right_index in range(min(2, len(right))):
                a, b = left[left_index], right[right_index]
                exact = (a.title, a.artist) == (b.title, b.artist)
                title_ratio = SequenceMatcher(None, a.title or "", b.title or "").ratio()
                artist_ratio = SequenceMatcher(None, a.artist or "", b.artist or "").ratio()
                if not exact and title_ratio >= 0.80 and artist_ratio >= 0.80:
                    if a.completeness_status == "COMPLETE_AS_OBSERVED":
                        left[left_index] = replace(a, completeness_status="TEXT_AMBIGUOUS", warnings=a.warnings + ("Conflicting adjacent-source text observation.",))
                    if b.completeness_status == "COMPLETE_AS_OBSERVED":
                        right[right_index] = replace(b, completeness_status="TEXT_AMBIGUOUS", warnings=b.warnings + ("Conflicting adjacent-source text observation.",))


def extract_screenshot_draft(
    extractor: ScreenshotExtractor,
    staged_sources: list[dict[str, object]],
) -> ScreenshotExtractionReview:
    observations = tuple(
        extractor.extract(str(source["source_key"]), Path(str(source["local_path"])))
        for source in staged_sources
    )
    return ScreenshotDraftReconciler().reconcile(observations)
