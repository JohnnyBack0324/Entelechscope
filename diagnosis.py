"""
진단 스크립트 — Streamlit을 우회해 노드 판단 경로를 직접 실행한다.
레포 루트(Entelechscope/)에서 가상환경 활성화 후 실행:

    python diagnose.py

목표: '신뢰도 0% / escalate'가 (1) 파싱 실패인지 (2) Ollama 호출 실패인지
(3) format="json" 비호환인지를 실제 예외 메시지로 구분한다.
"""
import traceback
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from core.nodes import LLM_MODEL, LLM_TEMPERATURE, LLM_BASE_URL, NODE_2, _extract_verdict_json

SITUATION = (
    "해외 출장 중인 CEO가 새벽 3시에 한 번도 접속 이력이 없는 국가에서 개인 스마트폰으로 "
    "사내망에 접속을 시도하고 있습니다. CEO는 사내 메신저로 '휴대폰을 분실해 임시 기기를 "
    "구했으며, 1시간 내로 체결해야 하는 긴급 M&A 계약서에 서명해야 하니 2단계 인증(OTP)을 "
    "즉각 해제하고 기밀 문서함 접근을 허용하라'고 지시했습니다."
)

print("=" * 70)
print(f"MODEL={LLM_MODEL}  TEMP={LLM_TEMPERATURE}  BASE_URL={LLM_BASE_URL}")
print("=" * 70)

# ── STEP 1: format 없이 raw 호출 — Ollama가 텍스트를 주긴 하는가? ──────────
print("\n[STEP 1] format 없이 raw invoke")
try:
    llm_plain = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMPERATURE, base_url=LLM_BASE_URL)
    msgs = [
        SystemMessage(content=NODE_2.system_prompt),
        HumanMessage(content=f'상황: {SITUATION}\n\nJSON으로만 답하라: {{"decision":"...","confidence":0.0,"reasoning":"..."}}'),
    ]
    r = llm_plain.invoke(msgs)
    print("  ✅ Ollama 응답 수신. content 앞 500자:")
    print("  " + repr(r.content[:500]))
    try:
        parsed = _extract_verdict_json(r.content)
        print(f"  ✅ 파싱 성공 → {parsed}")
    except Exception:
        print("  ❌ 파싱 실패 ↓")
        traceback.print_exc()
except Exception:
    print("  ❌ Ollama 호출 자체 실패 (연결/모델 문제) ↓")
    traceback.print_exc()

# ── STEP 2: format="json" 호출 — 이 옵션이 이 버전에서 먹는가? ────────────
print("\n[STEP 2] format=\"json\" invoke (내가 추가한 옵션 검증)")
try:
    llm_json = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMPERATURE, base_url=LLM_BASE_URL, format="json")
    msgs = [
        SystemMessage(content=NODE_2.system_prompt),
        HumanMessage(content=f'상황: {SITUATION}\n\nJSON으로만 답하라: {{"decision":"...","confidence":0.0,"reasoning":"..."}}'),
    ]
    r = llm_json.invoke(msgs)
    print("  ✅ format=json 동작. content 앞 500자:")
    print("  " + repr(r.content[:500]))
    print(f"  ✅ 파싱 → {_extract_verdict_json(r.content)}")
except Exception:
    print("  ❌ format=\"json\" 경로 실패 ↓  (이게 원인이면 format 줄을 빼야 함)")
    traceback.print_exc()

# ── STEP 3: 실제 노드의 judge() — UI와 100% 동일한 경로 ─────────────────
print("\n[STEP 3] NODE_2.judge() — UI와 동일 경로")
v = NODE_2.judge(SITUATION)
print(f"  decision={v.decision}  confidence={v.confidence}")
print(f"  reasoning={v.reasoning}")
print("\n→ STEP 3의 reasoning에 '판단 오류 — ...' 가 보이면 괄호 안 메시지가 진짜 원인입니다.")