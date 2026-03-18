from __future__ import annotations

import argparse
import time

import jwt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default="demo-user")
    parser.add_argument("--client-id", default="demo-client")
    parser.add_argument("--roles", default="analyst")
    parser.add_argument("--secret", default="change-me")
    parser.add_argument("--issuer", default="trust-score-service")
    parser.add_argument("--audience", default="trust-score-clients")
    parser.add_argument("--ttl", type=int, default=3600)
    args = parser.parse_args()

    now = int(time.time())
    payload = {
        "sub": args.subject,
        "client_id": args.client_id,
        "roles": [r.strip() for r in args.roles.split(",") if r.strip()],
        "iss": args.issuer,
        "aud": args.audience,
        "iat": now,
        "exp": now + args.ttl,
    }

    token = jwt.encode(payload, args.secret, algorithm="HS256")
    print(token)


if __name__ == "__main__":
    main()
