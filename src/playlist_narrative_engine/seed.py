from __future__ import annotations

from sqlalchemy.orm import Session

from playlist_narrative_engine.taste.ratings import Rating
from playlist_narrative_engine.taste.repository import ArtistRepository
from playlist_narrative_engine.taste.schemas import ArtistCreate


CALIBRATION_ARTISTS: tuple[tuple[str, str], ...] = (
    ("Glenn Miller", "Big band and swing"), ("Duke Ellington", "Big band and swing"),
    ("Benny Goodman", "Big band and swing"), ("Count Basie", "Big band and swing"),
    ("Ella Fitzgerald", "Jazz and swing"), ("Frank Sinatra", "Traditional pop"),
    ("The Beatles", "Classic rock"), ("The Rolling Stones", "Classic rock"),
    ("Led Zeppelin", "Classic rock"), ("The Who", "Classic rock"),
    ("Fleetwood Mac", "Classic rock"), ("Queen", "Classic rock"),
    ("Rush", "Progressive rock"), ("Yes", "Progressive rock"),
    ("Genesis", "Progressive rock"), ("King Crimson", "Progressive rock"),
    ("Pink Floyd", "Progressive rock"), ("Dream Theater", "Progressive metal"),
    ("Black Sabbath", "Heavy metal"), ("Iron Maiden", "Heavy metal"),
    ("Judas Priest", "Heavy metal"), ("Metallica", "Thrash metal"),
    ("Megadeth", "Thrash metal"), ("Slayer", "Thrash metal"),
    ("Anthrax", "Thrash metal"), ("Pantera", "Groove metal"),
    ("Tool", "Alternative metal"), ("System of a Down", "Alternative metal"),
    ("Nine Inch Nails", "Industrial"), ("Ministry", "Industrial"),
    ("KMFDM", "Industrial"), ("Rammstein", "Industrial metal"),
    ("Front 242", "EBM"), ("Nitzer Ebb", "EBM"),
    ("VNV Nation", "Futurepop"), ("Covenant", "Futurepop"),
    ("Bauhaus", "Goth"), ("Siouxsie and the Banshees", "Goth"),
    ("The Cure", "Goth and new wave"), ("Sisters of Mercy", "Goth"),
    ("Depeche Mode", "Synthpop"), ("New Order", "New wave"),
    ("Duran Duran", "New wave"), ("Tears for Fears", "New wave"),
    ("Pet Shop Boys", "Synthpop"), ("Gary Numan", "New wave"),
    ("The Chameleons", "Post-punk"), ("Lebanon Hanover", "Darkwave"),
    ("Boy Harsher", "Darkwave"), ("HEALTH", "Industrial electronic"),
    ("Nirvana", "Grunge"), ("Pearl Jam", "Grunge"),
    ("Soundgarden", "Grunge"), ("Alice in Chains", "Grunge"),
    ("Radiohead", "Alternative rock"), ("The Smashing Pumpkins", "Alternative rock"),
    ("Beastie Boys", "Hip-hop"), ("Run-D.M.C.", "Hip-hop"),
    ("Public Enemy", "Hip-hop"), ("N.W.A", "Gangster rap"),
    ("Dr. Dre", "Hip-hop"), ("Snoop Dogg", "Hip-hop"),
    ("Tupac Shakur", "Hip-hop"), ("The Notorious B.I.G.", "Hip-hop"),
    ("Kendrick Lamar", "Hip-hop"), ("Missy Elliott", "Hip-hop"),
    ("Daft Punk", "Electronic"), ("The Chemical Brothers", "Electronic"),
    ("The Prodigy", "Electronic"), ("Underworld", "Electronic"),
    ("Orbital", "Electronic"), ("Aphex Twin", "Electronic"),
    ("Jeff Mills", "Techno"), ("Charlotte de Witte", "Techno"),
    ("Kraftwerk", "Electronic"), ("Carpenter Brut", "Synthwave"),
    ("Perturbator", "Synthwave"), ("The Midnight", "Synthwave"),
    ("Girls' Generation", "K-pop"), ("SHINee", "K-pop"),
    ("BTS", "K-pop"), ("BLACKPINK", "K-pop"),
    ("TWICE", "K-pop"), ("aespa", "K-pop"),
    ("Stray Kids", "K-pop"), ("NewJeans", "K-pop"),
    ("KATSEYE", "Global pop"), ("Taylor Swift", "Modern pop"),
    ("Beyoncé", "Modern pop"), ("Lady Gaga", "Modern pop"),
    ("Dua Lipa", "Modern pop"), ("Billie Eilish", "Modern pop"),
    ("Chappell Roan", "Modern pop"), ("Sabrina Carpenter", "Modern pop"),
    ("Olivia Rodrigo", "Modern pop"), ("The Weeknd", "Modern pop"),
    ("Charli xcx", "Modern pop"), ("Doechii", "Hip-hop"),
    ("Sleep Token", "Alternative metal"), ("Spiritbox", "Metalcore"),
    ("Electric Callboy", "Electronicore"), ("Poppy", "Alternative pop"),
    ("BABYMETAL", "Kawaii metal"), ("Bloodywood", "Folk metal"),
    ("Viagra Boys", "Post-punk"), ("Fontaines D.C.", "Post-punk"),
)


def seed_calibration_artists(session: Session) -> int:
    repository = ArtistRepository(session)
    created = 0
    for name, group in CALIBRATION_ARTISTS:
        if repository.get_by_name(name) is not None:
            continue
        rating = Rating.FORBIDDEN if name == "Radiohead" else Rating.UNKNOWN
        repository.add(
            ArtistCreate(name=name, calibration_group=group, rating=rating)
        )
        created += 1
    return created

