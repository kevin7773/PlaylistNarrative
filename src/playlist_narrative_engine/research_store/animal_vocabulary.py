from __future__ import annotations

from collections.abc import Mapping

from playlist_narrative_engine.research_store.study_vocabulary import (
    FINITE_VOCABULARY_SCHEMA_VERSION,
    STANDALONE_MEMBER_MATCH_CONTRACT_ID,
    STANDALONE_MEMBER_MATCH_CONTRACT_SHA256,
    STANDALONE_MEMBER_MATCH_CONTRACT_VERSION,
    finite_vocabulary_sha256,
    verify_finite_vocabulary_plan,
)


ANIMAL_VOCABULARY_KEY = "animal-names"
ANIMAL_VOCABULARY_ID = "pne.research-vocabulary.animal-names"
ANIMAL_VOCABULARY_VERSION = "1.0"
ANIMAL_VOCABULARY_CASE_SENSITIVE = False

# Repository-owned curated common-English lexical instrument. This is
# intentionally bounded and is neither a taxonomy nor an exhaustive species
# list. Every accepted surface form is explicit; no morphology is inferred.
_MEMBERS = (
    "alligator", "alligators", "animal", "animals", "ant", "ants",
    "ape", "apes", "baboon", "baboons", "badger", "badgers", "bass", "bat", "bats",
    "bear", "bears", "bee", "bees", "beetle", "beetles", "bird", "birds",
    "bison", "blackbird", "blackbirds", "bluebird", "bluebirds", "boar", "boars",
    "bobcat", "bobcats", "buffalo", "bull", "bulls", "butterfly", "butterflies",
    "camel", "camels", "canary", "canaries", "cat", "catfish", "catfishes", "cats",
    "cheetah", "cheetahs", "chicken", "chickens", "chimp", "chimps", "chimpanzee",
    "chimpanzees", "clam", "clams", "cobra", "cobras", "cockatoo", "cockatoos",
    "condor", "condors", "coral", "cougar", "cougars", "cow", "cows", "coyote",
    "coyotes", "crab", "crabs", "crane", "cranes", "crocodile", "crocodiles",
    "crow", "crows", "deer", "dingo", "dingoes", "dinosaur", "dinosaurs", "dodo",
    "dodos", "dog", "dogs", "dolphin", "dolphins", "donkey", "donkeys", "dove",
    "doves", "dragonfly", "dragonflies", "duck", "ducks", "eagle", "eagles", "eel",
    "eels", "elephant", "elephants", "elk", "falcon", "falcons", "ferret",
    "ferrets", "finch", "finches", "firefly", "fireflies", "fish", "flamingo",
    "flamingos", "fly", "flies", "fox", "foxes", "frog", "frogs", "gazelle",
    "gazelles", "gecko", "geckos", "giraffe", "giraffes", "goat", "goats", "goose",
    "geese", "gorilla", "gorillas", "grasshopper", "grasshoppers", "gull", "gulls",
    "hamster", "hamsters", "hare", "hares", "hawk", "hawks", "hedgehog",
    "hedgehogs", "hen", "hens", "heron", "herons", "hippo", "hippos",
    "hippopotamus", "hippopotamuses", "hornet", "hornets", "horse", "horses",
    "hound", "hounds", "hummingbird", "hummingbirds", "hyena", "hyenas", "ibis",
    "ibises", "iguana", "iguanas", "insect", "insects", "jackal", "jackals",
    "jaguar", "jaguars", "jellyfish", "kangaroo", "kangaroos", "kitten", "kittens",
    "koala", "koalas", "ladybug", "ladybugs", "lamb", "lambs", "leopard",
    "leopards", "lion", "lions", "lizard", "lizards", "lobster", "lobsters",
    "lynx", "mammoth", "mammoths", "manatee", "manatees", "manta ray", "manta rays",
    "mare", "mares", "marlin", "mink", "minks", "mole", "moles", "monkey",
    "monkeys", "moose", "mosquito", "mosquitoes", "moth", "moths", "mouse", "mice",
    "mule", "mules", "mustang", "mustangs", "newt", "newts", "nightingale",
    "nightingales", "octopus", "octopuses", "opossum", "opossums", "orangutan",
    "orangutans", "orca", "orcas", "ostrich", "ostriches", "otter", "otters", "owl",
    "owls", "ox", "oxen", "oyster", "oysters", "panda", "pandas", "panther",
    "panthers", "parrot", "parrots", "peacock", "peacocks", "pelican", "pelicans",
    "penguin", "penguins", "pig", "pigs", "pigeon", "pigeons", "pony", "ponies",
    "porcupine", "porcupines", "possum", "possums", "prawn", "prawns", "puffin",
    "puffins", "puppy", "puppies", "quail", "rabbit", "rabbits", "raccoon",
    "raccoons", "ram", "rams", "rat", "rats", "raven", "ravens", "rhino", "rhinos",
    "rhinoceros", "rhinoceroses", "robin", "robins", "rooster", "roosters", "salmon",
    "scorpion", "scorpions", "seal", "seals", "seahorse", "seahorses", "shark",
    "sharks", "sheep", "shrimp", "skunk", "skunks", "sloth", "sloths", "slug",
    "slugs", "snail", "snails", "snake", "snakes", "sparrow", "sparrows", "spider",
    "spiders", "squid", "squirrels", "squirrel", "starfish", "stingray", "stingrays",
    "swan", "swans", "tiger", "tigers", "toad", "toads", "trout", "tuna", "turkey",
    "turkeys", "turtle", "turtles", "vulture", "vultures", "walrus", "walruses", "wasp",
    "wasps", "weasel", "weasels", "whale", "whales", "wolf", "wolves", "wombat",
    "wombats", "woodpecker", "woodpeckers", "worm", "worms", "yak", "yaks", "zebra",
    "zebras",
)


def _term_key(value: str) -> str:
    return value.replace(" ", "-").replace("'", "-apostrophe-")


ANIMAL_VOCABULARY_TERMS = tuple(
    {
        "vocabulary_key": ANIMAL_VOCABULARY_KEY,
        "term_key": _term_key(value),
        "term_definition": value,
    }
    for value in sorted(_MEMBERS, key=lambda item: item.encode("utf-8"))
)

ANIMAL_VOCABULARY_SHA256 = (
    "c63f9de32ebfc76b4ff622f68bf3422a062a4a9afbdb120f94a4a40b8aec95cb"
)


def animal_vocabulary_parameters() -> tuple[dict[str, object], ...]:
    return (
        {"parameter_key": "vocabulary_key", "value_type": "TEXT", "text_value": ANIMAL_VOCABULARY_KEY},
        {"parameter_key": "vocabulary_schema_version", "value_type": "TEXT", "text_value": FINITE_VOCABULARY_SCHEMA_VERSION},
        {"parameter_key": "vocabulary_id", "value_type": "TEXT", "text_value": ANIMAL_VOCABULARY_ID},
        {"parameter_key": "vocabulary_version", "value_type": "TEXT", "text_value": ANIMAL_VOCABULARY_VERSION},
        {"parameter_key": "vocabulary_sha256", "value_type": "TEXT", "text_value": ANIMAL_VOCABULARY_SHA256},
        {"parameter_key": "matching_contract_id", "value_type": "TEXT", "text_value": STANDALONE_MEMBER_MATCH_CONTRACT_ID},
        {"parameter_key": "matching_contract_version", "value_type": "TEXT", "text_value": STANDALONE_MEMBER_MATCH_CONTRACT_VERSION},
        {"parameter_key": "matching_contract_sha256", "value_type": "TEXT", "text_value": STANDALONE_MEMBER_MATCH_CONTRACT_SHA256},
        {"parameter_key": "case_sensitive", "value_type": "BOOLEAN", "boolean_value": ANIMAL_VOCABULARY_CASE_SENSITIVE},
    )


def animal_vocabulary_parameter_values() -> dict[str, object]:
    return {
        item["parameter_key"]: item.get("boolean_value", item.get("text_value"))
        for item in animal_vocabulary_parameters()
    }


def verify_animal_vocabulary_publication(
    *, terms: tuple[Mapping[str, object], ...] = ANIMAL_VOCABULARY_TERMS,
    parameters: Mapping[str, object] | None = None,
) -> tuple[str, ...]:
    values = dict(parameters or animal_vocabulary_parameter_values())
    plan = {"vocabulary_terms": list(terms)}
    members = verify_finite_vocabulary_plan(plan, values)
    if (
        values.get("vocabulary_key") != ANIMAL_VOCABULARY_KEY
        or values.get("vocabulary_id") != ANIMAL_VOCABULARY_ID
        or values.get("vocabulary_version") != ANIMAL_VOCABULARY_VERSION
        or values.get("vocabulary_sha256") != ANIMAL_VOCABULARY_SHA256
        or values.get("case_sensitive") is not ANIMAL_VOCABULARY_CASE_SENSITIVE
    ):
        raise ValueError("Animal Vocabulary v1.0 publication authority was substituted")
    return members


_computed_digest = finite_vocabulary_sha256(
    vocabulary_id=ANIMAL_VOCABULARY_ID,
    vocabulary_version=ANIMAL_VOCABULARY_VERSION,
    vocabulary_key=ANIMAL_VOCABULARY_KEY,
    terms=ANIMAL_VOCABULARY_TERMS,
)
if _computed_digest != ANIMAL_VOCABULARY_SHA256:
    raise RuntimeError("Animal Vocabulary v1.0 changed without a successor version")
