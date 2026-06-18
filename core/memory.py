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
            "case_id": result.case_id,
            "timestamp": datetime.now().isoformat(),
            "situation": situation,
            "status": result.status,
            "final_decision": result.final_decision,
            "is_consensus": result.is_consensus,
            "avg_confidence": result.avg_confidence,
            "vote_count": result.vote_count,
            "requires_human": result.requires_human,
            "dissenting_node": result.dissenting_node,
            "veto_triggered": result.veto_triggered,
            "base_decision": result.base_decision,
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

    def find_by_case_id(self, case_id: str) -> list:
        """같은 사안(case_id)에 대한 과거 판단 모두 검색.
        같은 사안에 다른 답이 나왔을 때 추적용."""
        if not self.log_path.exists():
            return []
        results = []
        for line in self.log_path.read_text(encoding="utf-8").strip().split("\n"):
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("case_id") == case_id:
                results.append(entry)
        return results

    def clear(self) -> int:
        """모든 판단 기록을 삭제한다. 삭제한 항목 수를 반환.
        영구 감사 로그 삭제이므로 호출 측에서 확인 절차를 거쳐야 한다."""
        if not self.log_path.exists():
            return 0
        count = sum(1 for line in self.log_path.read_text(encoding="utf-8").splitlines() if line.strip())
        self.log_path.unlink()
        return count