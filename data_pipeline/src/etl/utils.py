from __future__ import annotations

import re
import time
from typing import Dict

SENTIMENT_LEXICON: Dict[str, int] = {
    "fraude": -3,
    "roubo": -3,
    "vazamento": -3,
    "ataque": -2,
    "risco": -2,
    "alerta": -2,
    "suspenso": -2,
    "recall": -2,
    "multa": -2,
    "processo": -2,
    "ganho": 2,
    "lucro": 2,
    "solido": 2,
    "crescimento": 2,
    "expansao": 2,
    "melhora": 2,
}


def rate_limit_sleep(min_interval_sec: float, last_ts: float) -> float:
    now = time.time()
    elapsed = now - last_ts
    if elapsed < min_interval_sec:
        time.sleep(min_interval_sec - elapsed)
    return time.time()


def simple_sentiment(text: str) -> int:
    if not text:
        return 0
    tokens = re.findall(r"\w+", text.lower())
    score = 0
    for token in tokens:
        score += SENTIMENT_LEXICON.get(token, 0)
    return score
