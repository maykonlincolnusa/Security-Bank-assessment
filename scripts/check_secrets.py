from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "models/output"}
EXCLUDED_FILES = {".env.example", "LICENSE"}

PATTERNS = {
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private_key": re.compile(r"-----BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY-----"),
    "generic_token": re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]"),
    "github_pat": re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
}


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if not path.is_file() or path.name in EXCLUDED_FILES:
            continue
        files.append(path)
    return files


def main() -> int:
    findings: list[str] = []

    for file_path in iter_files():
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for name, pattern in PATTERNS.items():
            for match in pattern.finditer(content):
                findings.append(f"{file_path.relative_to(ROOT)}:{name}:{match.group(0)[:64]}")

    if findings:
        print("Potential secret leaks found:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("No obvious secret leaks found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
