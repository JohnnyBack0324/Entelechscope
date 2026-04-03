# 감사 추적

import json
from datetime import datetime
from pathlib import Path

class MemoryLog:
    def __init__(self, log_path: str = "data/decisions.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(exist_ok=True)
    
    def record(self, situation: str, result) -> str:
        entry = {
            "id": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
            "timestamp": datetime.now().isoformat(),
            "situation": situation,
            "final_decision": result.final_decision,
            "is_consensus": result.is_consensus,
            "vote_count": result.vote_count,
            "requires_human": result.requires_human,
            "dissenting_node": result.dissenting_node,
            "verdicts": [v.model_dump() for v in result.verdicts]
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return entry["id"]

    def load_recent(self, n: int = 20) -> list:
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text(encoding="utf-8").strip().split("\n")
        return [json.loads(l) for l in lines[-n:] if l]