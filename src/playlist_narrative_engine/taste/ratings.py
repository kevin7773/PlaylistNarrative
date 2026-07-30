from __future__ import annotations

from enum import StrEnum


class Rating(StrEnum):
    LOVE = "Love"
    LIKE = "Like"
    MEH = "Meh"
    NO_THANKS = "No Thanks"
    PENCIL = "Pencil"
    FORBIDDEN = "Forbidden"
    UNKNOWN = "Unknown"


DEFAULT_EXCLUDED_RATINGS = frozenset(
    {Rating.NO_THANKS, Rating.PENCIL, Rating.FORBIDDEN}
)


def is_normally_eligible(rating: Rating) -> bool:
    return rating not in DEFAULT_EXCLUDED_RATINGS

