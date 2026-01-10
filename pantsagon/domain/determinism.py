import os


def is_deterministic() -> bool:
    return os.getenv("PANTSAGON_DETERMINISTIC") == "1"
