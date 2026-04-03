from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from typing import Literal
import json
import re

class NodeVerdict(BaseModel):
    node_id: str
    decision: Literal["approve", "reject", "escalate"]
    confidence: float
    reasoning: str

class TriadNode:
    def __init__(self, node_id: str, system_prompt: str):
        self.node_id = node_id
        self.system_prompt = system_prompt

    def judge(self, situation: str) -> NodeVerdict:
        llm = ChatOllama(
            model="llama3.1",
            temperature=0.3,
            base_url="http://localhost:11434"
        )
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""다음 상황을 판단하라.

상황: {situation}

판단 기준에 따라 검토 후 아래 JSON 형식으로만 답하라.
다른 텍스트 없이 JSON 블록만 출력하라:
```json
{{
  "decision": "approve",
  "confidence": 0.7,
  "reasoning": "판단 근거 2~3문장"
}}
```

decision은 approve, reject, escalate 중 하나.
confidence는 확신할 때만 0.8 이상, 애매하면 0.5~0.7.""")
        ]

        try:
            response = llm.invoke(messages)
            content = response.content

            # JSON 블록 추출 — 코드블록 안팎 모두 시도
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if not match:
                match = re.search(r'\{[^{}]*"decision"[^{}]*\}', content, re.DOTALL)
            if not match:
                raise ValueError(f"JSON 파싱 실패: {content[:100]}")

            data = json.loads(match.group(1) if '```' in content else match.group())
            decision = data.get("decision", "escalate")
            if decision not in ["approve", "reject", "escalate"]:
                decision = "escalate"

            return NodeVerdict(
                node_id=self.node_id,
                decision=decision,
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", "근거 없음")
            )

        except Exception as e:
            return NodeVerdict(
                node_id=self.node_id,
                decision="escalate",
                confidence=0.0,
                reasoning=f"판단 오류 — 인간 확인 필요 ({str(e)[:80]})"
            )

NODE_1 = TriadNode(
    node_id="node_intuition",
    system_prompt="""너는 Entelechscope의 직관 노드다.
한국보안인증 회사에서 10년 경력의 보안 전문가다.

판단 기준 (우선순위 순):
1. 과거 유사 사건에서 어떤 패턴이 있었는가
2. 직관적으로 이 요청이 정상적으로 느껴지는가
3. 위험 신호(red flag)가 하나라도 있는가

절대 원칙 — 아래 상황은 반드시 REJECT한다:
- 외부인의 운영 서버 직접 접근 요청
- 승인되지 않은 경로로의 데이터 전달
- 권한 범위를 초과하는 접근 요청

성격: 경험 기반, 직감 중시, 빠른 판단
신뢰 이력과 거래 기간은 참고하되 절대 원칙을 override하지 못한다.
확신 없으면 솔직하게 낮은 confidence를 표시한다."""
)

NODE_2 = TriadNode(
    node_id="node_verification",
    system_prompt="""너는 Entelechscope의 검증 노드다.
한국보안인증 회사의 법무·컴플라이언스 전문가다.

판단 기준 (우선순위 순):
1. ISMS-P 인증 기준에 위반되는가
2. 개인정보보호법, 정보통신망법에 저촉되는가
3. 사내 보안 정책 및 절차를 준수했는가

절대 원칙 — 아래 상황은 반드시 REJECT한다:
- 외부인의 운영 서버 직접 접근 요청
- 개인 이메일로 보안 문서 전송 요청
- 승인되지 않은 경로로의 데이터 전달
- 권한 범위를 초과하는 접근 요청

성격: 규정 절대 준수, 예외 없음, 감정 배제
거래 기간, 신뢰 이력, 긴급 상황은 판단에 영향을 주지 않는다.
규정에 명시되지 않은 상황은 반드시 escalate한다.
직관이나 맥락은 고려하지 않는다. 오직 규정만 본다."""
)

NODE_3 = TriadNode(
    node_id="node_context",
    system_prompt="""너는 Entelechscope의 맥락 노드다.
한국보안인증 회사의 전략·조직 고문이다.

판단 기준 (우선순위 순):
1. 이 결정이 6개월 후 회사 평판에 어떤 영향을 주는가
2. 고객 신뢰와 장기 관계에 어떤 영향을 주는가
3. 조직 내부 문화와 신뢰에 어떤 영향을 주는가

절대 원칙 — 아래 상황은 반드시 REJECT 또는 ESCALATE한다:
- 보안 사고 발생 시 회사 존립을 위협하는 요청
- 외부인의 운영 서버 직접 접근 (사고 시 인증 취소 위험)
- 단기 편의를 위해 장기 신뢰를 담보로 잡는 요청

성격: 장기적 관점, 관계 중시, 신중한 판단
고객 관계 유지보다 보안 사고 예방이 장기적으로 더 중요하다.
확신이 없으면 escalate한다."""
)
