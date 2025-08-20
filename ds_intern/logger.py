import os
import json
from datetime import datetime
from typing import Any, Dict


def write_run_metadata(out_dir: str, metadata: Dict[str, Any]) -> None:
	os.makedirs(out_dir, exist_ok=True)
	path = os.path.join(out_dir, f"run_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json")
	with open(path, "w", encoding="utf-8") as f:
		json.dump(metadata, f, ensure_ascii=False, indent=2)