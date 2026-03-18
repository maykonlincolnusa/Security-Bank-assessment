from __future__ import annotations

from pathlib import Path


REQUIRED_PATHS = [
    "data_pipeline",
    "models",
    "api_service",
    "infra",
    "security",
    "dashboard",
    "docs",
    ".github/workflows",
    "docker-compose.yml",
    "Makefile",
    "README.md",
    "LICENSE",
    ".gitignore",
    ".env.example",
]


def test_required_structure_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED_PATHS if not (root / path).exists()]
    assert not missing, f"Missing required paths: {missing}"
