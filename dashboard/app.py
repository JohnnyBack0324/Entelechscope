import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from core.consensus import ConsensusEngine, case_hash
from core.memory import MemoryLog
from core.stability import run_stability_check
from core.health import check_ollama

st.set_page_config(
    page_title="Entelechscope - 한국보안인증",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Entelechscope")
st.caption("트라이어드 합의 엔진 - Phase 0 데모")

engine = ConsensusEngine()
memory = MemoryLog()


# ── 안전한 데이터 관리를 위한 콜백 함수 정의 ───────────────────────
def clear_records_callback():
    """판단 기록을 삭제하고 체크박스 상태를 안전하게 초기화합니다."""
    deleted = memory.clear()
    st.session_state["deleted_records_msg"] = f"{deleted}건의 판단 기록을 삭제했습니다."
    st.session_state["confirm_records"] = False

def clear_cache_callback():
    """캐시와 세션 상태를 비우고 알림 메시지를 설정합니다."""
    st.cache_data.clear()
    st.cache_resource.clear()
    st.session_state.clear()
    st.session_state["cleared_cache_msg"] = "세션 캐시와 위젯 상태를 비웠습니다."


# ── 사이드바: 시스템 상태 + 관리 ────────────────────────────────
with st.sidebar:
    st.header("시스템 상태")

    health = check_ollama()
    if health.status_level == "ok":
        st.success(health.status_message)
    elif health.status_level == "warning":
        st.warning(health.status_message)
    else:
        st.error(health.status_message)

    with st.expander("LLM 설정 상세"):
        st.text(f"모델: {health.configured_model}")
        st.text(f"Base URL: {health.base_url}")
        st.text(f"Temperature: {health.temperature}")
        if health.server_reachable:
            st.caption(f"설치된 모델 ({len(health.installed_models)}개):")
            for m in health.installed_models:
                is_active = (
                    m == health.configured_model
                    or m.split(":")[0] == health.configured_model.split(":")[0]
                )
                marker = "● " if is_active else "○ "
                st.text(f"  {marker}{m}")

    if st.button("🔄 상태 새로고침", use_container_width=True):
        st.rerun()

    st.divider()
    st.header("데이터 관리")

    st.caption("**판단 기록 지우기**")
    st.caption("`data/decisions.jsonl`의 모든 판단 기록을 영구 삭제합니다.")
    confirm_records = st.checkbox("기록 삭제에 동의합니다", key="confirm_records")
    st.button(
        "🗑 판단 기록 전체 삭제",
        use_container_width=True,
        disabled=not confirm_records,
        type="secondary",
        on_click=clear_records_callback  # 콜백 함수 연결
    )
    
    # 콜백 실행 후 성공 알림 출력
    if "deleted_records_msg" in st.session_state:
        st.success(st.session_state["deleted_records_msg"])
        del st.session_state["deleted_records_msg"]

    st.divider()

    st.caption("**세션 캐시 지우기**")
    st.caption("Streamlit 캐시와 위젯 상태를 비웁니다. 입력값이 초기화됩니다.")
    confirm_cache = st.checkbox("캐시 삭제에 동의합니다", key="confirm_cache")
    st.button(
        "♻ 세션 캐시 전체 삭제",
        use_container_width=True,
        disabled=not confirm_cache,
        type="secondary",
        on_click=clear_cache_callback  # 콜백 함수 연결
    )
    
    # 콜백 실행 후 성공 알림 출력
    if "cleared_cache_msg" in st.session_state:
        st.success(st.session_state["cleared_cache_msg"])
        del st.session_state["cleared_cache_msg"]

    st.divider()


# ── 시스템 흐름도 ───────────────────────────────────────────────
with st.expander("▶ 시스템 흐름도"):
    st.code("""                    상황 입력
                       │
      ┌────────────────┼────────────────┐
      ▼                ▼                ▼
 ⚡ 직관 노드      📋 검증 노드      🌐 맥락 노드
 (병렬 추론)       (병렬 추론)       (병렬 추론)
      │                │                │
      └────────────────┼────────────────┘
                       ▼
                 다수결 집계
                       │
             검증 노드 가중 거부권 검사 (conf ≥ 0.9)
                       │
              평균 confidence 검사 (< 0.6)
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
       합의 도달            불일치 / 저신뢰 / 거부권
            │                     │
            ▼                     ▼
       결과 반환           🚨 인간 승인 게이트
            │
            ▼
      세션 기록 (감사 추적)""", language=None)
    st.caption(
        "세 노드는 ThreadPoolExecutor로 병렬 호출 · 검증 노드는 가중 거부권 보유 · "
        "평균 confidence < 0.6 시 인간 검토 권장"
    )


def render_result(result, decision_id=None):
    """단일 ConsensusResult 표시."""
    decision_color = {"approve": "🟢", "reject": "🔴", "escalate": "🟡"}
    status_label = {
        "UNANIMOUS": "✅ 만장일치",
        "MAJORITY": "◐ 2/3 다수결",
        "VETO": "⚠ 가중 거부권 발동",
        "LOW_CONFIDENCE": "◐ 저신뢰 합의",
        "DEADLOCK": "✗ 합의 실패",
    }

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "최종 판단",
            f"{decision_color.get(result.final_decision, '')} {result.final_decision.upper()}"
        )
    with col2:
        st.metric("합의 상태", status_label.get(result.status, result.status))
    with col3:
        st.metric("평균 확신도", f"{result.avg_confidence:.0%}")
    with col4:
        st.metric("인간 개입", "필요" if result.requires_human else "불필요")

    if result.veto_triggered:
        st.error(
            f"⚠ **가중 거부권 발동** — 검증 노드가 강한 확신으로 REJECT했습니다. "
            f"기본 다수결은 `{result.base_decision}`였으나 ESCALATE로 강제 전환되었습니다. "
            f"(규정 위반은 다수결로 뒤집을 수 없습니다)"
        )

    if result.status == "LOW_CONFIDENCE":
        st.warning(
            f"◐ **저신뢰 합의** — 결론은 모였으나 세 노드 평균 확신이 "
            f"{result.avg_confidence:.0%}로 낮습니다. 인간 검토를 권장합니다."
        )

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
        is_veto_source = (
            result.veto_triggered and verdict.node_id == "node_verification"
        )
        label = node_names.get(verdict.node_id, verdict.node_id)
        if is_veto_source:
            label += " ⚠ 거부권 행사"
        elif is_dissent:
            label += " ⚠ 이탈"
        with st.expander(
            f"{label} → {verdict.decision.upper()} (신뢰도: {verdict.confidence:.0%})"
        ):
            st.write(verdict.reasoning)

    if result.requires_human:
        st.error("🚨 인간 승인 필요 — 이 판단은 담당자 검토 후 실행하세요")

    cap_parts = [f"사안 ID: `{result.case_id}`"]
    if decision_id:
        cap_parts.append(f"판단 ID: `{decision_id}`")
    st.caption(" · ".join(cap_parts))


# ── 입력 ─────────────────────────────────────────────────────────
situation = st.text_area(
    "판단이 필요한 상황을 입력하세요",
    placeholder="예: 외부 업체가 내부 서버 접근 권한을 요청했습니다. 해당 업체는 3년 거래처이며 이번 프로젝트 마감일이 내일입니다.",
    height=120
)

if situation:
    st.caption(f"이 사안의 추적 ID: `{case_hash(situation)}`")

col_a, col_b = st.columns([1, 1])
with col_a:
    run_single = st.button("⚡ 트라이어드 판단 시작", type="primary", use_container_width=True)
with col_b:
    run_stability = st.button(
        "🔁 안정성 검사 (×5)",
        use_container_width=True,
        help="같은 사안을 5회 반복 시행해 답의 일관성을 측정합니다"
    )

# 모델이 사용 불가능한 상태에서 버튼이 눌리면 미리 경고하고 중단
if (run_single or run_stability) and not health.model_available:
    st.error(
        f"모델 `{health.configured_model}`이 사용 불가능합니다. "
        f"왼쪽 사이드바에서 상태를 확인하세요."
    )
    run_single = False
    run_stability = False

# ── 단일 판단 ────────────────────────────────────────────────────
if run_single and situation:
    with st.spinner("세 노드가 독립적으로 판단 중..."):
        result = engine.run(situation)
        decision_id = memory.record(situation, result)
    render_result(result, decision_id)

# ── 안정성 검사 ──────────────────────────────────────────────────
if run_stability and situation:
    progress = st.progress(0, text="안정성 검사 시작…")

    with st.spinner("같은 사안을 5회 반복 시행 중…"):
        stab = run_stability_check(situation, n=5)
    progress.progress(1.0, text="안정성 검사 완료")

    stab_color = "🟢" if stab.stability >= 0.8 else "🟡" if stab.stability >= 0.6 else "🔴"
    stab_label = "높음" if stab.stability >= 0.8 else "보통" if stab.stability >= 0.6 else "낮음"

    st.subheader("안정성 진단")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("안정성", f"{stab_color} {stab.stability:.0%}")
    sc2.metric("일관성 수준", stab_label)
    sc3.metric("우세 결론", f"{stab.dominant_count}/{stab.n}")

    st.info(stab.interpretation)

    st.subheader("결과 분포")
    for status_label, count in stab.distribution:
        ratio = count / stab.n
        st.write(f"**{status_label}** — {count}/{stab.n} 시행 ({ratio:.0%})")
        st.progress(ratio)

    st.subheader("노드별 일관성")
    node_names = {
        "node_intuition": "⚡ 직관",
        "node_verification": "📋 검증",
        "node_context": "🌐 맥락",
    }
    for ns in stab.node_stability:
        name = node_names.get(ns.node_id, ns.node_id)
        st.write(
            f"**{name}** — 일관성 {ns.stability:.0%} · 시퀀스: `{' · '.join(ns.verdicts)}`"
        )
        st.progress(ns.stability)

    with st.expander("5회 시행 상세"):
        for i, trial in enumerate(stab.trials, 1):
            verdicts_str = " / ".join(v.decision.upper() for v in trial.verdicts)
            st.text(
                f"시행 {i}: {trial.status} → {trial.final_decision.upper()} "
                f"(평균 확신 {trial.avg_confidence:.0%}, [{verdicts_str}])"
            )

    st.caption(f"사안 ID: `{case_hash(situation)}` · 안정성 검사는 기록에 저장되지 않습니다")


# ── 최근 판단 기록 ──────────────────────────────────────────────
st.divider()
st.subheader("최근 판단 기록")
recent = memory.load_recent(10)
if recent:
    for entry in reversed(recent):
        color = {"approve": "🟢", "reject": "🔴", "escalate": "🟡"}
        status_icon = {
            "UNANIMOUS": "✅",
            "MAJORITY": "◐",
            "VETO": "⚠",
            "LOW_CONFIDENCE": "◐",
            "DEADLOCK": "✗",
        }
        status = entry.get("status", "UNANIMOUS" if entry.get("is_consensus") else "DEADLOCK")
        avg_c = entry.get("avg_confidence")
        avg_str = f" · 평균 {avg_c:.0%}" if avg_c is not None else ""
        case_id = entry.get("case_id", "—")
        st.text(
            f"{entry['timestamp'][:16]}  "
            f"{status_icon.get(status, '·')} {status}  "
            f"{color.get(entry['final_decision'], '')} {entry['final_decision'].upper()}"
            f"{avg_str}  |  [{case_id}] {entry['situation'][:50]}..."
        )
else:
    st.caption("아직 판단 기록이 없습니다.")