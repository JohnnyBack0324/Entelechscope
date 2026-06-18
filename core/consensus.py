from core.nodes import NodeVerdict, NODE_1, NODE_2, NODE_3
from pydantic import BaseModel
from typing import Optional, Literal
import concurrent.futures
import hashlib
import os

# ── 합의 판정 임계값 ───────────────────────────────────────────────
CONSENSUS_THRESHOLD = int(os.getenv("CONSENSUS_THRESHOLD", 2))
VETO_CONFIDENCE_THRESHOLD = float(os.getenv("VETO_CONFIDENCE_THRESHOLD", 0.9))
LOW_CONFIDENCE_THRESHOLD = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", 0.6))

# 합의 상태 — 단순히 'requires_human'만으로는 *왜* 인간 개입이 필요한지 추적이 어려움.
# 명시적 상태로 분리해서 감사 추적과 UI 표시에 활용한다.
ConsensusStatus = Literal[
    "UNANIMOUS",       # 3/3 일치
    "MAJORITY",        # 2/3 일치
    "VETO",            # 검증 노드 가중 거부권 발동
    "LOW_CONFIDENCE",  # 합의는 도달했으나 평균 confidence < 0.6
    "DEADLOCK"         # 3자 불일치
]


def case_hash(situation: str) -> str:
    """사안 텍스트에서 짧은 추적 ID 생성. 같은 사안이 반복되었는지 식별에 사용."""
    h = hashlib.sha256(situation.strip().encode("utf-8")).hexdigest()
    return "ENT-" + h[:7].upper()


class ConsensusResult(BaseModel):
    case_id: str
    status: ConsensusStatus
    final_decision: str
    is_consensus: bool
    vote_count: dict
    verdicts: list[NodeVerdict]
    dissenting_node: Optional[str]
    requires_human: bool
    avg_confidence: float
    # 가중 거부권이 발동했을 때, 거부권 발동 전의 다수결 결과를 보존
    base_decision: Optional[str] = None
    veto_triggered: bool = False


class ConsensusEngine:
    def __init__(self):
        self.nodes = [NODE_1, NODE_2, NODE_3]
        self.threshold = CONSENSUS_THRESHOLD

    def run(self, situation: str) -> ConsensusResult:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(node.judge, situation)
                for node in self.nodes
            ]
            verdicts = [f.result() for f in futures]

        return self._aggregate(situation, verdicts)

    def _aggregate(self, situation: str, verdicts: list[NodeVerdict]) -> ConsensusResult:
        """판단 집계 — run() 외에 안정성 검사(stability.py)에서도 재사용."""
        vote_count = {"approve": 0, "reject": 0, "escalate": 0}
        for v in verdicts:
            vote_count[v.decision] += 1

        avg_confidence = sum(v.confidence for v in verdicts) / 3

        # 기본 다수결
        base_decision = max(vote_count, key=vote_count.get)
        top_count = vote_count[base_decision]
        is_consensus = top_count >= self.threshold

        # 이탈 노드 식별 (다수결 결과와 다른 노드)
        dissenting = None
        if is_consensus and top_count < 3:
            for v in verdicts:
                if v.decision != base_decision:
                    dissenting = v.node_id
                    break

        # 가중 거부권 — 검증 노드가 강한 확신으로 REJECT
        # 임계값을 1.0에서 0.9로 낮춤: LLM이 1.0을 거의 출력하지 않아 실질 미발동 문제 해결
        verification_verdict = next(
            (v for v in verdicts if v.node_id == "node_verification"), None
        )
        veto_triggered = (
            is_consensus
            and base_decision == "approve"
            and verification_verdict is not None
            and verification_verdict.decision == "reject"
            and verification_verdict.confidence >= VETO_CONFIDENCE_THRESHOLD
        )

        # 상태 결정 — 우선순위: VETO > DEADLOCK > LOW_CONFIDENCE > UNANIMOUS/MAJORITY
        if veto_triggered:
            status = "VETO"
            final_decision = "escalate"
        elif not is_consensus:
            status = "DEADLOCK"
            final_decision = "escalate"  # 합의 없음 → 안전하게 보류
        elif avg_confidence < LOW_CONFIDENCE_THRESHOLD:
            status = "LOW_CONFIDENCE"
            final_decision = base_decision
        elif top_count == 3:
            status = "UNANIMOUS"
            final_decision = base_decision
        else:
            status = "MAJORITY"
            final_decision = base_decision

        requires_human = status in ("VETO", "DEADLOCK", "LOW_CONFIDENCE") or final_decision == "escalate"

        return ConsensusResult(
            case_id=case_hash(situation),
            status=status,
            final_decision=final_decision,
            is_consensus=is_consensus and not veto_triggered,
            vote_count=vote_count,
            verdicts=verdicts,
            dissenting_node=dissenting,
            requires_human=requires_human,
            avg_confidence=avg_confidence,
            base_decision=base_decision if veto_triggered else None,
            veto_triggered=veto_triggered,
        )