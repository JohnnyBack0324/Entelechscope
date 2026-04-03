import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from core.consensus import ConsensusEngine
from core.memory import MemoryLog

st.set_page_config(
    page_title="Entelechscope - 한국보안인증",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Entelechscope")
st.caption("트라이어드 합의 엔진 - Phase 0 데모")

engine = ConsensusEngine()
memory = MemoryLog()

situation = st.text_area(
    "판단이 필요한 상황을 입력하세요",
    placeholder="예: 외부 업체가 내부 서버 접근 권한을 요청했습니다. 해당 업체는 3년 거래처이며 이번 프로젝트 마감일이 내일입니다.",
    height=120
)

if st.button("⚡ 트라이어드 판단 시작", type="primary"):
    if situation:
        with st.spinner("세 노드가 독립적으로 판단 중..."):
            result = engine.run(situation)
            decision_id = memory.record(situation, result)

        col1, col2, col3 = st.columns(3)
        decision_color = {"approve": "🟢", "reject": "🔴", "escalate": "🟡"}

        with col1:
            st.metric("최종 판단", f"{decision_color.get(result.final_decision, '')} {result.final_decision.upper()}")
        with col2:
            st.metric("합의 여부", "✅ 합의" if result.is_consensus else "⚠️ 불일치")
        with col3:
            st.metric("인간 개입", "필요" if result.requires_human else "불필요")

        st.subheader("투표 현황")
        vote_cols = st.columns(3)
        for i, (decision, count) in enumerate(result.vote_count.items()):
            vote_cols[i].metric(decision.upper(), f"{count}/3")

        st.subheader("노드별 판단 근거")
        node_names = {
            "node_intuition": "⚡ 노드 1 — 직관",
            "node_verification": "📋 노드 2 — 검증",
            "node_context": "🌐 노드 3 — 맥락"
        }

        for verdict in result.verdicts:
            is_dissent = verdict.node_id == result.dissenting_node
            label = node_names.get(verdict.node_id, verdict.node_id)
            if is_dissent:
                label += " ⚠️ 이탈"
            with st.expander(f"{label} → {verdict.decision.upper()} (신뢰도: {verdict.confidence:.0%})"):
                st.write(verdict.reasoning)

        if result.dissenting_node:
            st.warning(f"이탈 노드 감지: {node_names.get(result.dissenting_node)} - 판단 불일치 기록됨")

        if result.requires_human:
            st.error("🚨 인간 승인 필요 — 이 판단은 담당자 검토 후 실행하세요")

        st.caption(f"판단 ID: {decision_id}")

st.divider()
st.subheader("최근 판단 기록")
recent = memory.load_recent(10)
if recent:
    for entry in reversed(recent):
        color = {"approve": "🟢", "reject": "🔴", "escalate": "🟡"}
        consensus = "✅" if entry["is_consensus"] else "⚠️"
        st.text(f"{entry['timestamp'][:16]}  {consensus}  {color.get(entry['final_decision'], '')} {entry['final_decision'].upper()}  |  {entry['situation'][:60]}...")
else:
    st.caption("아직 판단 기록이 없습니다.")