from core.nodes import NodeVerdict, NODE_1, NODE_2, NODE_3
from pydantic import BaseModel
from typing import Optional
import concurrent.futures
import os

class ConsensusResult(BaseModel):
    final_decision: str
    is_consensus: bool
    vote_count: dict
    verdicts: list[NodeVerdict]
    dissenting_node: Optional[str]
    requires_human: bool

class ConsensusEngine:
    def __init__(self):
        self.nodes = [NODE_1, NODE_2, NODE_3]
        self.threshold = int(os.getenv("CONSENSUS_THRESHOLD", 2))

    def run(self, situation: str) -> ConsensusResult:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(node.judge, situation)
                for node in self.nodes
            ]
            verdicts = [f.result() for f in futures]

        vote_count = {"approve": 0, "reject": 0, "escalate": 0}
        for v in verdicts:
            vote_count[v.decision] += 1

        final_decision = max(vote_count, key=vote_count.get)
        is_consensus = vote_count[final_decision] >= self.threshold

        # 가중 거부권 — 검증 노드가 100% 확신으로 REJECT하면 ESCALATE 강제
        verification_verdict = next(
            (v for v in verdicts if v.node_id == "node_verification"), None
        )
        if (verification_verdict and
            verification_verdict.decision == "reject" and
            verification_verdict.confidence >= 1.0 and
            final_decision == "approve"):
            final_decision = "escalate"
            is_consensus = False

        dissenting = None
        if is_consensus:
            for v in verdicts:
                if v.decision != final_decision:
                    dissenting = v.node_id

        avg_confidence = sum(v.confidence for v in verdicts) / 3
        requires_human = (
            not is_consensus or
            final_decision == "escalate" or
            avg_confidence < 0.6
        )

        return ConsensusResult(
            final_decision=final_decision,
            is_consensus=is_consensus,
            vote_count=vote_count,
            verdicts=verdicts,
            dissenting_node=dissenting,
            requires_human=requires_human
        )