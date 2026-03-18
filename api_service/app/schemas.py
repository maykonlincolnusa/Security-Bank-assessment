from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictStr


class ScoreResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    institution_id: StrictStr
    trust_score: StrictFloat
    explanation: Dict[str, StrictFloat]


class ScoreItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    institution_id: StrictStr
    features: Optional[Dict[StrictStr, StrictFloat]] = None


class BatchScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: List[ScoreItem] = Field(..., min_length=1, max_length=500)


class BatchScoreResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    results: List[ScoreResponse]
