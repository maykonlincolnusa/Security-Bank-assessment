from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"

REQUIRED_KEYS = {
    "ENVIRONMENT",
    "KMS_KEY_ID",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "ETL_DB_URL",
    "OPEN_BANKING_CLIENT_ID",
    "OPEN_BANKING_CLIENT_SECRET",
    "NEWS_API_KEY",
    "SERVICE_DB_URL",
    "REDIS_URL",
    "JWT_SECRET",
    "AGENT_SIGNING_SECRET",
    "TRUST_SCORE_URL",
}


def parse_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        keys.add(key)
    return keys


def main() -> int:
    if not ENV_EXAMPLE.exists():
        print(f"Missing file: {ENV_EXAMPLE}")
        return 1

    keys = parse_keys(ENV_EXAMPLE)
    missing = sorted(REQUIRED_KEYS - keys)

    if missing:
        print(".env.example is missing required keys:")
        for item in missing:
            print(f"- {item}")
        return 1

    print(".env.example validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
