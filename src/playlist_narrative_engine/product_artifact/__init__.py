"""Canonical, auditable product result for a completed Penny construction."""

from playlist_narrative_engine.product_artifact.canonical import (
    final_product_content_sha256,
    serialize_final_product_artifact,
    serialize_final_product_content,
    verify_final_product_digest,
)
from playlist_narrative_engine.product_artifact.finalizer import (
    FinalProductFinalizer,
    resolve_final_placement_authorities,
    verify_final_product_artifact,
)
from playlist_narrative_engine.product_artifact.schemas import (
    FINAL_PRODUCT_SCHEMA_VERSION,
    ConstituentAuthority,
    FinalProductArtifact,
    FinalProductContent,
    PlacementAuthorityReference,
    RefinementDisposition,
)

__all__ = [
    "FINAL_PRODUCT_SCHEMA_VERSION",
    "ConstituentAuthority",
    "FinalProductArtifact",
    "FinalProductContent",
    "FinalProductFinalizer",
    "PlacementAuthorityReference",
    "RefinementDisposition",
    "final_product_content_sha256",
    "resolve_final_placement_authorities",
    "serialize_final_product_artifact",
    "serialize_final_product_content",
    "verify_final_product_artifact",
    "verify_final_product_digest",
]
