import hashlib
import hmac
import json
import os
import sys

ALLOWED_SKILLS = {"trust-score-skill", "news-summary"}
BLACKLIST = {"skill-dangerous-001"}


def validate_skill(skill_id: str) -> bool:
    if skill_id in BLACKLIST:
        return False
    return skill_id in ALLOWED_SKILLS


def simulate_agent_request(agent_id: str, skill_id: str, secret: str, path: str, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    msg = f"{agent_id}:POST:{path}".encode("utf-8") + body
    signature = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return {"X-Agent-Id": agent_id, "X-Agent-Skill": skill_id, "X-Agent-Signature": signature}


def main():
    agent_id = "agent-001"
    skill_id = sys.argv[1] if len(sys.argv) > 1 else "trust-score-skill"
    secret = os.getenv("AGENT_SIGNING_SECRET", "change-me")

    if not validate_skill(skill_id):
        print("Skill rejected")
        sys.exit(1)

    headers = simulate_agent_request(agent_id, skill_id, secret, "/score/001", {"foo": "bar"})
    print("Headers:", headers)
    print("Skill accepted")


if __name__ == "__main__":
    main()
