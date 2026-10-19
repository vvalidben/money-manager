"""Command-line flags read before the user interface is loaded."""

from collections.abc import Sequence
from pathlib import Path

SELF_TEST_FLAG = "--self-test"


def self_test_folder(argv: Sequence[str]) -> Path | None:
    """The folder given after ``--self-test``, if the flag is present."""
    arguments = list(argv)
    if SELF_TEST_FLAG not in arguments:
        return None
    index = arguments.index(SELF_TEST_FLAG)
    if index + 1 >= len(arguments):
        raise SystemExit(f"{SELF_TEST_FLAG} needs a folder")
    return Path(arguments[index + 1]).resolve()
