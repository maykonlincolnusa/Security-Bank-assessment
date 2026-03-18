from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PIPELINE_SRC = ROOT / "data_pipeline" / "src"
API_SERVICE_ROOT = ROOT / "api_service"

for path in (ROOT, DATA_PIPELINE_SRC, API_SERVICE_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)
