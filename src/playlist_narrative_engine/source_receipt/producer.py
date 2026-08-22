from __future__ import annotations

import base64

from playlist_narrative_engine.source_receipt.artifact import (
    FROZEN_SOURCE_RECEIPT_AUTHORITY,
    SourceObservationRequest,
    SourceReceiptArtifact,
    SourceReceiptContent,
    SourceReceiptItem,
    source_receipt_content_sha256,
    source_receipt_id,
)
from playlist_narrative_engine.source_receipt.definitions import (
    ACQUISITION_INTERFACE_DEFINITION,
    CANONICAL_SERIALIZATION_PROFILE,
    CAPTURE_POINT_DEFINITION,
    SOURCE_RECEIPT_POLICY,
    verify_source_receipt_authority_definition,
)


class SourceReceiptInvalidInput(ValueError):
    """The observation cannot authorize a Source Receipt artifact."""


class SourceReceiptProducer:
    """Sole production authority for observation-only Source Receipt artifacts."""

    def produce_authoritative(
        self,
        request: SourceObservationRequest,
    ) -> SourceReceiptArtifact:
        if not isinstance(request, SourceObservationRequest):
            raise SourceReceiptInvalidInput(
                "source receipt production requires a governed observation request"
            )
        try:
            validated = SourceObservationRequest.model_validate(
                request.model_dump(mode="python")
            )
            self._verify_frozen_authority(validated)
            if not validated.complete_response:
                raise ValueError("source response must be complete")
            if validated.declared_item_count != len(validated.items):
                raise ValueError("declared item count must match observed items")
            handles = tuple(item.observation_handle for item in validated.items)
            if SOURCE_RECEIPT_POLICY.has_duplicate_observation_handles(handles):
                raise ValueError("observation handles must be unique within the event")

            items = tuple(
                SourceReceiptItem(
                    item_id=f"item-{ordinal:06d}",
                    ordinal=ordinal,
                    observation_handle=item.observation_handle,
                    payload_base64=base64.b64encode(item.payload).decode("ascii"),
                )
                for ordinal, item in enumerate(validated.items, start=1)
            )
            content = SourceReceiptContent(
                authority=validated.authority,
                source_type=validated.source_type,
                source_reference=validated.source_reference,
                complete_response=True,
                declared_item_count=validated.declared_item_count,
                items=items,
            )
            digest = source_receipt_content_sha256(content)
            return SourceReceiptArtifact(
                receipt_id=source_receipt_id(digest),
                receipt_content_sha256=digest,
                authority=content.authority,
                source_type=content.source_type,
                source_reference=content.source_reference,
                complete_response=content.complete_response,
                declared_item_count=content.declared_item_count,
                items=content.items,
            )
        except (TypeError, ValueError) as exc:
            if isinstance(exc, SourceReceiptInvalidInput):
                raise
            raise SourceReceiptInvalidInput(
                "source receipt authority is invalid or observation is incomplete"
            ) from exc

    @staticmethod
    def _verify_frozen_authority(request: SourceObservationRequest) -> None:
        definitions = (
            CANONICAL_SERIALIZATION_PROFILE,
            ACQUISITION_INTERFACE_DEFINITION,
            CAPTURE_POINT_DEFINITION,
            SOURCE_RECEIPT_POLICY,
        )
        if not all(
            verify_source_receipt_authority_definition(value)
            for value in definitions
        ):
            raise ValueError("frozen Source Receipt authority does not verify")
        if request.authority != FROZEN_SOURCE_RECEIPT_AUTHORITY:
            raise ValueError("observation request must bind exact frozen authority")


def verify_source_receipt_artifact(
    artifact: SourceReceiptArtifact,
    *,
    request: SourceObservationRequest,
) -> bool:
    if not isinstance(artifact, SourceReceiptArtifact):
        return False
    try:
        validated_artifact = SourceReceiptArtifact.model_validate(
            artifact.model_dump(mode="json")
        )
        validated_request = SourceObservationRequest.model_validate(
            request.model_dump(mode="python")
        )
        reproduced = SourceReceiptProducer().produce_authoritative(validated_request)
    except (TypeError, ValueError):
        return False
    return validated_artifact == artifact == reproduced
