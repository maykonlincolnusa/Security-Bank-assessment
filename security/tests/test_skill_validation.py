from skill_validation import validate_skill


def test_skill_blacklist_denied():
    assert validate_skill("skill-dangerous-001") is False


def test_skill_allowlist_accepted():
    assert validate_skill("trust-score-skill") is True


def test_unknown_skill_denied():
    assert validate_skill("unknown-skill") is False
