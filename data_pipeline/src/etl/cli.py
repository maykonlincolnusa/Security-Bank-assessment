from __future__ import annotations

from .config import load_settings
from .pipeline import run_daily


def main() -> None:
    settings = load_settings()
    run_daily(settings)


if __name__ == "__main__":
    main()
