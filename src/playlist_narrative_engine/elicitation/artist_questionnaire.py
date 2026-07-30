from __future__ import annotations

import json

from playlist_narrative_engine.elicitation.schemas import (
    ArtistQuestionnaireEntry,
    ArtistQuestionnaireRequest,
    ArtistQuestionnaireSeed,
    ArtistSeedEvidence,
    InclusionBasis,
)


def _utf8_key(value: str) -> bytes:
    return value.encode("utf-8")


class ArtistQuestionnaireSeedGenerator:
    """Build a closed-world questionnaire seed from explicit evidence only."""

    def generate(
        self,
        request: ArtistQuestionnaireRequest,
    ) -> ArtistQuestionnaireSeed:
        evidence_by_artist: dict[str, list[ArtistSeedEvidence]] = {}
        for evidence in request.seed_evidence:
            evidence_by_artist.setdefault(evidence.artist_name, []).append(evidence)

        entries = tuple(
            ArtistQuestionnaireEntry(
                ordinal=ordinal,
                artist_name=artist_name,
                inclusion_basis=InclusionBasis.EXPLICIT_SEED_EVIDENCE,
                source_evidence=tuple(
                    sorted(
                        evidence_by_artist[artist_name],
                        key=lambda evidence: _utf8_key(evidence.evidence_id),
                    )
                ),
                inclusion_explanation=(
                    f"Included because supplied seed evidence explicitly names "
                    f"{artist_name!r}."
                ),
            )
            for ordinal, artist_name in enumerate(
                sorted(evidence_by_artist, key=_utf8_key),
                start=1,
            )
        )

        return ArtistQuestionnaireSeed(
            objective=request.objective,
            approved_local_rules=request.approved_local_rules,
            entries=entries,
        )


def serialize_artist_questionnaire_seed(
    artifact: ArtistQuestionnaireSeed,
) -> bytes:
    """Return canonical schema-order JSON with no environment-dependent spacing."""

    serialized = json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return serialized.encode("utf-8")
