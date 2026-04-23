import json
from pathlib import Path
def load_cfg(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))
