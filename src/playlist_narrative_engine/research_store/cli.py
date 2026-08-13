from __future__ import annotations

import argparse
import json

from playlist_narrative_engine.research_store.database import make_research_engine, make_research_session_factory
from playlist_narrative_engine.research_store.exporter import export_csv_bundle, export_json
from playlist_narrative_engine.research_store.importer import (
    import_research_export, load_experiment_documents,
    load_persisted_artifact_documents,
)
from playlist_narrative_engine.research_store.migrations import migrate_research_database
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import (
    ConstraintStatus, ExperimentAssessmentOutcome, GenerationFailureInput,
)
from playlist_narrative_engine.research_store.service import ResearchStoreService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pne-research")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db", help="Initialize or migrate the research database")
    importer = commands.add_parser("import-json", help="Import experiment JSON")
    importer.add_argument("path")
    export_importer = commands.add_parser("import-export-json", help="Import a complete v2 research export")
    export_importer.add_argument("path")
    artifact_importer = commands.add_parser("import-artifact-json", help="Import persisted-artifact JSON")
    artifact_importer.add_argument("path")
    failure = commands.add_parser("record-failure", help="Record a failed generation")
    failure.add_argument("--prompt", required=True)
    failure.add_argument("--failure-type", required=True)
    failure.add_argument("--message", required=True)
    failure.add_argument("--source-system", default="Maestro Beta")
    failure.add_argument("--notes")
    show = commands.add_parser("show", help="Show one complete experiment as JSON")
    show.add_argument("experiment_id", type=int)
    show_artifact = commands.add_parser("show-artifact", help="Show one persisted artifact as JSON")
    show_artifact.add_argument("artifact_id", type=int)
    recurring_tracks = commands.add_parser("recurring-tracks")
    recurring_tracks.add_argument("--limit", type=int, default=20)
    recurring_artists = commands.add_parser("recurring-artists")
    recurring_artists.add_argument("--limit", type=int, default=20)
    track_occurrences = commands.add_parser("track-occurrences")
    track_occurrences.add_argument("canonical_track_id", type=int)
    artist_occurrences = commands.add_parser("artist-occurrences")
    artist_occurrences.add_argument("canonical_artist")
    track_profile = commands.add_parser("track-profile")
    track_profile.add_argument("canonical_track_id", type=int)
    artist_profile = commands.add_parser("artist-profile")
    artist_profile.add_argument("canonical_artist")
    recurring_track_profiles = commands.add_parser("recurring-track-profiles")
    recurring_track_profiles.add_argument("--limit", type=int, default=20)
    recurring_artist_profiles = commands.add_parser("recurring-artist-profiles")
    recurring_artist_profiles.add_argument("--limit", type=int, default=20)
    compare = commands.add_parser("compare-experiments")
    compare.add_argument("experiment_id_a", type=int)
    compare.add_argument("experiment_id_b", type=int)
    track_cooccurrences = commands.add_parser("track-cooccurrences")
    track_cooccurrences.add_argument("canonical_track_id", type=int)
    track_cooccurrences.add_argument("--limit", type=int, default=20)
    artist_cooccurrences = commands.add_parser("artist-cooccurrences")
    artist_cooccurrences.add_argument("canonical_artist")
    artist_cooccurrences.add_argument("--limit", type=int, default=20)
    track_pair = commands.add_parser("track-pair-occurrences")
    track_pair.add_argument("canonical_track_id_a", type=int)
    track_pair.add_argument("canonical_track_id_b", type=int)
    artist_pair = commands.add_parser("artist-pair-occurrences")
    artist_pair.add_argument("canonical_artist_a")
    artist_pair.add_argument("canonical_artist_b")
    recurring_track_pairs = commands.add_parser("recurring-track-pairs")
    recurring_track_pairs.add_argument("--limit", type=int, default=20)
    recurring_track_pairs.add_argument("--minimum-shared-experiments", type=int, default=2)
    recurring_artist_pairs = commands.add_parser("recurring-artist-pairs")
    recurring_artist_pairs.add_argument("--limit", type=int, default=20)
    recurring_artist_pairs.add_argument("--minimum-shared-experiments", type=int, default=2)
    labels = commands.add_parser("tracks-across-labels", help="Query explicit human-assigned prompt labels")
    labels.add_argument("--minimum-labels", type=int, default=2)
    query = commands.add_parser("query")
    query.add_argument("--assessment")
    query.add_argument(
        "--assessment-outcome",
        choices=[item.value for item in ExperimentAssessmentOutcome],
    )
    query.add_argument("--constraint-status", choices=[item.value for item in ConstraintStatus])
    saved = query.add_mutually_exclusive_group()
    saved.add_argument("--saved", action="store_true", dest="saved_filter")
    saved.add_argument("--not-saved", action="store_false", dest="saved_filter")
    query.set_defaults(saved_filter=None)
    json_export = commands.add_parser("export-json")
    json_export.add_argument("path")
    csv_export = commands.add_parser("export-csv")
    csv_export.add_argument("directory")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    engine = make_research_engine()
    read_only_commands = {
        "show", "show-artifact", "recurring-tracks", "recurring-artists",
        "track-occurrences", "artist-occurrences", "tracks-across-labels", "query",
        "track-profile", "artist-profile", "recurring-track-profiles",
        "recurring-artist-profiles", "compare-experiments",
        "track-cooccurrences", "artist-cooccurrences", "track-pair-occurrences",
        "artist-pair-occurrences", "recurring-track-pairs", "recurring-artist-pairs",
    }
    version = None
    if args.command not in read_only_commands:
        version = migrate_research_database(engine)
    if args.command == "init-db":
        print(f"Research database ready at schema version {version}.")
        return
    sessions = make_research_session_factory(engine)
    with sessions() as session:
        repository = ResearchRepository(session)
        service = ResearchStoreService(repository)
        if args.command == "import-json":
            experiment_ids = [
                service.ingest_experiment(item).record_id
                for item in load_experiment_documents(args.path)
            ]
            print(json.dumps({"experiment_ids": experiment_ids}))
        elif args.command == "import-export-json":
            print(json.dumps(import_research_export(repository, args.path)))
        elif args.command == "import-artifact-json":
            artifact_ids = [
                service.ingest_persisted_artifact(item).record_id
                for item in load_persisted_artifact_documents(args.path)
            ]
            print(json.dumps({"persisted_artifact_ids": artifact_ids}))
        elif args.command == "record-failure":
            failure_id = repository.record_generation_failure(GenerationFailureInput(
                prompt=args.prompt, source_system=args.source_system,
                failure_type=args.failure_type, displayed_message=args.message, notes=args.notes,
            ))
            print(json.dumps({"generation_failure_id": failure_id}))
        elif args.command == "show":
            print(json.dumps(service.get_experiment(args.experiment_id), indent=2))
        elif args.command == "show-artifact":
            print(json.dumps(service.get_persisted_artifact(args.artifact_id), indent=2))
        elif args.command == "recurring-tracks":
            print(json.dumps(service.recurring_tracks(args.limit), indent=2))
        elif args.command == "recurring-artists":
            print(json.dumps(service.recurring_artists(args.limit), indent=2))
        elif args.command == "track-occurrences":
            print(json.dumps(service.track_occurrences(args.canonical_track_id), indent=2))
        elif args.command == "artist-occurrences":
            print(json.dumps(service.artist_occurrences(args.canonical_artist), indent=2))
        elif args.command == "track-profile":
            print(json.dumps(service.track_profile(args.canonical_track_id), indent=2))
        elif args.command == "artist-profile":
            print(json.dumps(service.artist_profile(args.canonical_artist), indent=2))
        elif args.command == "recurring-track-profiles":
            print(json.dumps(service.recurring_track_profiles(args.limit), indent=2))
        elif args.command == "recurring-artist-profiles":
            print(json.dumps(service.recurring_artist_profiles(args.limit), indent=2))
        elif args.command == "compare-experiments":
            print(json.dumps(service.compare_experiments(
                args.experiment_id_a, args.experiment_id_b,
            ), indent=2))
        elif args.command == "track-cooccurrences":
            print(json.dumps(service.track_cooccurrences(
                args.canonical_track_id, args.limit,
            ), indent=2))
        elif args.command == "artist-cooccurrences":
            print(json.dumps(service.artist_cooccurrences(
                args.canonical_artist, args.limit,
            ), indent=2))
        elif args.command == "track-pair-occurrences":
            print(json.dumps(service.track_pair_occurrences(
                args.canonical_track_id_a, args.canonical_track_id_b,
            ), indent=2))
        elif args.command == "artist-pair-occurrences":
            print(json.dumps(service.artist_pair_occurrences(
                args.canonical_artist_a, args.canonical_artist_b,
            ), indent=2))
        elif args.command == "recurring-track-pairs":
            print(json.dumps(service.recurring_track_pairs(
                args.limit, args.minimum_shared_experiments,
            ), indent=2))
        elif args.command == "recurring-artist-pairs":
            print(json.dumps(service.recurring_artist_pairs(
                args.limit, args.minimum_shared_experiments,
            ), indent=2))
        elif args.command == "tracks-across-labels":
            print(json.dumps(repository.tracks_across_prompt_labels(minimum_distinct_labels=args.minimum_labels), indent=2))
        elif args.command == "query":
            print(json.dumps(service.query_experiments(
                assessment=args.assessment,
                assessment_outcome=args.assessment_outcome,
                constraint_status=args.constraint_status, saved=args.saved_filter,
            ), indent=2))
        elif args.command == "export-json":
            print(export_json(repository, args.path))
        elif args.command == "export-csv":
            print(export_csv_bundle(repository, args.directory))


if __name__ == "__main__":
    main()
