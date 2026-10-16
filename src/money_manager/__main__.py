"""Entry point: ``python -m money_manager``."""

import sys

from money_manager.app import run


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
