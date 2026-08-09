from __future__ import annotations

import argparse
import json

from playlist_narrative_engine.research_store.database import make_research_engine, make_research_session_factory
from playlist_narrative_engine.research_store.exporter import export_csv_bundle, export_json
from playlist_narrative_engine.research_store.importer import (
    import_experiment_documents, import_persisted_artifact_documents,
    import_research_export,
)
from playlist_narrative_engine.research_store.migrations import migrate_research_database
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ConstraintStatus, GenerationFailureInput


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
    labels = commands.add_parser("tracks-across-labels", help="Query explicit human-assigned prompt labels")
    labels.add_argument("--minimum-labels", type=int, default=2)
    query = commands.add_parser("query")
    query.add_argument("--assessment")
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
    version = migrate_research_database(engine)
    if args.command == "init-db":
        print(f"Research database ready at schema version {version}.")
        return
    sessions = make_research_session_factory(engine)
    with sessions() as session:
        repository = ResearchRepository(session)
        if args.command == "import-json":
            print(json.dumps({"experiment_ids": import_experiment_documents(repository, args.path)}))
        elif args.command == "import-export-json":
            print(json.dumps(import_research_export(repository, args.path)))
        elif args.command == "import-artifact-json":
            print(json.dumps({"persisted_artifact_ids": import_persisted_artifact_documents(repository, args.path)}))
        elif args.command == "record-failure":
            failure_id = repository.record_generation_failure(GenerationFailureInput(
                prompt=args.prompt, source_system=args.source_system,
                failure_type=args.failure_type, displayed_message=args.message, notes=args.notes,
            ))
            print(json.dumps({"generation_failure_id": failure_id}))
        elif args.command == "show":
            print(json.dumps(repository.get_experiment(args.experiment_id), indent=2))
        elif args.command == "show-artifact":
            print(json.dumps(repository.get_persisted_artifact(args.artifact_id), indent=2))
        elif args.command == "recurring-tracks":
            print(json.dumps(repository.recurring_tracks(args.limit), indent=2))
        elif args.command == "recurring-artists":
            print(json.dumps(repository.recurring_artists(args.limit), indent=2))
        elif args.command == "tracks-across-labels":
            print(json.dumps(repository.tracks_across_prompt_labels(minimum_distinct_labels=args.minimum_labels), indent=2))
        elif args.command == "query":
            print(json.dumps(repository.query_experiments(
                assessment=args.assessment, constraint_status=args.constraint_status, saved=args.saved_filter,
            ), indent=2))
        elif args.command == "export-json":
            print(export_json(repository, args.path))
        elif args.command == "export-csv":
            print(export_csv_bundle(repository, args.directory))


if __name__ == "__main__":
    main()
