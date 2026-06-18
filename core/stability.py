# 안정성 검사 — 같은 사안을 N회 반복해서 답이 얼마나 일관적인지 측정한다.
# LLM은 temperature > 0 환경에서 매번 같은 답을 주지 않는다. 이 변이 자체를 진단 정보로 활용한다.

from core.consensus import ConsensusEngine, ConsensusResult
from pydantic import BaseModel
from typing import List


class NodeStability(BaseModel):
    node_id: str
    stability: float          # 0.0~1.0, N회 중 가장 많이 나온 답의 비율
    verdicts: List[str]       # 각 시행에서 그 노드가 낸 verdict 시퀀스


class StabilityResult(BaseModel):
    n: int
    dominant_status: str
    dominant_count: int
    stability: float                       # 합의 결과의 일관성 (0.0~1.0)
    distribution: List[tuple]              # [(status_label, count), ...]
    node_stability: List[NodeStability]
    trials: List[ConsensusResult]
    interpretation: str


def _status_label(result: ConsensusResult) -> str:
    """안정성 분석을 위해 status + decision을 합친 라벨을 만든다."""
    if result.status in ("UNANIMOUS", "MAJORITY", "LOW_CONFIDENCE"):
        return f"{result.status}:{result.final_decision}"
    return result.status  # VETO, DEADLOCK은 decision이 의미가 약함


def _interpret(stability: float) -> str:
    if stability >= 1.0:
        return "완전한 일관성 — 이 사안은 시스템에게 명확합니다"
    if stability >= 0.8:
        return "안정적 — 우세한 결론을 신뢰할 수 있습니다"
    if stability >= 0.6:
        return "흔들림 있음 — 결론은 우세하지만 맥락 변수가 작용합니다. 추가 정보 권장"
    return "분열 — 시스템 내부가 합의에 이르지 못합니다. 인간 판단이 필요합니다"


def run_stability_check(situation: str, n: int = 5) -> StabilityResult:
    """같은 사안을 n회 반복 시행하고 결과의 일관성을 분석한다."""
    engine = ConsensusEngine()
    trials: List[ConsensusResult] = []
    for _ in range(n):
        trials.append(engine.run(situation))

    # 합의 결과 분포
    status_counts: dict = {}
    for t in trials:
        label = _status_label(t)
        status_counts[label] = status_counts.get(label, 0) + 1
    distribution = sorted(status_counts.items(), key=lambda x: x[1], reverse=True)
    dominant_status, dominant_count = distribution[0]
    overall_stability = dominant_count / n

    # 노드별 일관성
    node_ids = [v.node_id for v in trials[0].verdicts]
    node_stab: List[NodeStability] = []
    for nid in node_ids:
        verdicts_seq = []
        for t in trials:
            v = next((v for v in t.verdicts if v.node_id == nid), None)
            verdicts_seq.append(v.decision if v else "—")
        counts: dict = {}
        for v in verdicts_seq:
            counts[v] = counts.get(v, 0) + 1
        top = max(counts.values()) if counts else 0
        node_stab.append(NodeStability(
            node_id=nid,
            stability=top / n if n > 0 else 0.0,
            verdicts=verdicts_seq,
        ))

    return StabilityResult(
        n=n,
        dominant_status=dominant_status,
        dominant_count=dominant_count,
        stability=overall_stability,
        distribution=distribution,
        node_stability=node_stab,
        trials=trials,
        interpretation=_interpret(overall_stability),
    )