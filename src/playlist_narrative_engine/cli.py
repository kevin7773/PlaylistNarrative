from __future__ import annotations

import argparse
import json

from playlist_narrative_engine.db import (
    initialize_database,
    make_engine,
    make_session_factory,
)
from playlist_narrative_engine.journey import ActiveFocusRequest, JourneyPlanner
from playlist_narrative_engine.seed import seed_calibration_artists
from playlist_narrative_engine.taste.ratings import Rating
from playlist_narrative_engine.taste.repository import ArtistRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pne")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db", help="Initialize and seed the local database")

    listing = commands.add_parser("list-artists", help="List calibration artists")
    listing.add_argument("--rating", choices=[rating.value for rating in Rating])

    rating = commands.add_parser("rate", help="Rate or re-rate an artist")
    rating.add_argument("artist")
    rating.add_argument("rating", choices=[value.value for value in Rating])
    rating.add_argument("--notes")

    focus = commands.add_parser(
        "plan-focus",
        help="Create a non-authoritative deterministic Active Focus planning demo",
    )
    focus.add_argument("--minutes", type=int, default=90)
    focus.add_argument("--discovery", type=int, default=20)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    engine = make_engine()
    initialize_database(engine)
    sessions = make_session_factory(engine)
    with sessions() as session:
        if args.command == "init-db":
            created = seed_calibration_artists(session)
            print(f"Database ready; added {created} calibration artists.")
        elif args.command == "list-artists":
            repository = ArtistRepository(session)
            selected = Rating(args.rating) if args.rating else None
            for artist in repository.list(selected):
                print(f"{artist.name}\t{artist.rating}\t{artist.calibration_group or ''}")
        elif args.command == "rate":
            artist = ArtistRepository(session).set_rating(
                args.artist, Rating(args.rating), args.notes
            )
            print(f"{artist.name}: {artist.rating}")
        elif args.command == "plan-focus":
            request = ActiveFocusRequest(
                duration_minutes=args.minutes,
                discovery_percent=args.discovery,
            )
            plan = JourneyPlanner().plan_active_focus(request)
            print(
                json.dumps(
                    {
                        "authority": "NON_AUTHORITATIVE_DEMO",
                        "warning": (
                            "This utility does not perform Objective Assessment or "
                            "Objective Safety and does not produce a JourneyPlanArtifact."
                        ),
                        "plan": plan.model_dump(mode="json"),
                    },
                    indent=2,
                )
            )


if __name__ == "__main__":
    main()
