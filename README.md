# 🧠 Entelechscope

> 서로 다른 페르소나를 가진 3개의 LLM이 하나의 안건을 독립적으로 심의하고,
> 다수결로 합의를 도출해 의사결정을 보조하는 **트라이어드 합의 엔진**(Triad Consensus Engine).

단일 모델의 판단은 편향되거나 한쪽으로 치우치기 쉽습니다. Entelechscope는 하나의 상황을
**직관 · 검증 · 맥락**이라는 세 관점으로 동시에 심의하게 하고, 그 투표 결과를 종합합니다.
세 노드의 의견이 갈리거나 확신이 낮으면 자동으로 **사람의 개입**을 요구합니다.

이름은 아리스토텔레스의 *엔텔레케이아(entelecheia, 잠재태의 현실화)* 와 *scope(관찰)* 의 합성어로,
"가능성을 여러 관점에서 들여다본다"는 의도를 담고 있습니다.

---

## 핵심 개념

| 노드 | 페르소나 | 판단 기준 |
| --- | --- | --- |
| ⚡ **직관 (intuition)** | 10년차 보안 전문가 | 과거 유사 사건의 패턴, 직감, red flag 유무 |
| 📋 **검증 (verification)** | 법무·컴플라이언스 전문가 | ISMS-P, 개인정보보호법·정보통신망법, 사내 보안 정책 준수 여부 |
| 🌐 **맥락 (context)** | 전략·조직 고문 | 회사 평판, 고객 신뢰, 장기 관계에 미치는 영향 |

각 노드는 동일한 상황을 받아 독립적으로 `approve`(승인) · `reject`(거부) · `escalate`(보류·상신)
중 하나를 투표하며, 판단의 신뢰도(confidence)와 근거(reasoning)를 함께 반환합니다.

### 합의 로직

1. **다수결** — 세 표 중 가장 많은 결정을 채택합니다. 임계값(`CONSENSUS_THRESHOLD`, 기본 2)
   이상을 얻으면 합의로 간주합니다.
2. **가중 거부권** — 검증 노드가 confidence 1.0으로 `reject`하면, 다수결 결과가 `approve`라도
   `escalate`로 강제 전환됩니다. (규정 위반은 다수결로 뒤집을 수 없다는 원칙)
3. **인간 개입 트리거** — 아래 중 하나라도 해당하면 사람의 최종 검토를 요구합니다.
   - 합의 실패(의견 불일치)
   - 최종 결정이 `escalate`
   - 세 노드의 평균 confidence가 0.6 미만
4. **감사 추적** — 모든 판단은 타임스탬프, 투표 현황, 노드별 근거와 함께 JSONL로 기록됩니다.

---

## 빠른 시작

### 사전 요구사항

- Python 3.11+
- [Ollama](https://ollama.com/) — 로컬 LLM 추론 엔진
- `llama3.1` 모델

```bash
# Ollama 설치 후 모델 다운로드
ollama pull llama3.1

# Ollama 서버 실행 (기본 포트 11434)
ollama serve
```

### 설치

먼저 저장소를 클론합니다.

```bash
git clone https://github.com/JohnnyBack0324/Entelechscope.git
cd Entelechscope
```

가상환경은 아래 두 방식 중 하나를 선택합니다. **conda 방식을 권장합니다** —
패키지가 시스템 경로와 섞이지 않고, 실행 파일 경로(`streamlit` 등)가 자동으로 잡혀
`command not found` 같은 PATH 문제가 발생하지 않습니다.

#### 방식 A — conda (권장)

```bash
# 가상환경 생성 및 활성화
conda create -n entelechscope python=3.11 -y
conda activate entelechscope

# 의존성 설치
pip install -r requirements.txt
```

> 활성화하면 프롬프트 앞에 `(entelechscope)` 가 표시됩니다.
> 다음 작업 세션에서는 `conda activate entelechscope` 만 다시 실행하면 됩니다.

#### 방식 B — venv

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

> 활성화하면 프롬프트 앞에 `(venv)` 가 표시됩니다.

### 실행

가상환경이 활성화된 상태에서 실행합니다.

```bash
streamlit run dashboard/app.py
```

> `streamlit: command not found` 가 뜬다면 가상환경이 활성화되지 않은 것입니다.
> `conda activate entelechscope`(또는 `source venv/bin/activate`)를 먼저 실행하세요.
> 그래도 안 되면 모듈로 직접 실행할 수 있습니다: `python -m streamlit run dashboard/app.py`

브라우저에서 `http://localhost:8501` 로 접속한 뒤, 판단이 필요한 상황을 입력하고
**⚡ 트라이어드 판단 시작** 버튼을 누르면 세 노드의 투표 결과와 근거를 확인할 수 있습니다.

---

## 사용 예시

입력:

```
외부 업체가 내부 운영 서버 접근 권한을 요청했습니다.
해당 업체는 3년 거래처이며, 이번 프로젝트 마감일이 내일입니다.
```

이 경우 세 노드의 절대 원칙(외부인의 운영 서버 직접 접근 금지)에 따라
거래 기간·긴급성과 무관하게 `reject` 또는 `escalate`로 수렴하며,
대시보드는 노드별 판단 근거와 최종 결정, 인간 개입 필요 여부를 함께 표시합니다.

---

## 프로젝트 구조

```
Entelechscope/
├── core/
│   ├── nodes.py        # TriadNode 정의 + 세 페르소나 시스템 프롬프트
│   ├── consensus.py    # ConsensusEngine — 다수결·가중 거부권·합의 판정
│   └── memory.py       # MemoryLog — 판단 기록 감사 추적(JSONL)
├── dashboard/
│   └── app.py          # Streamlit 데모 UI
├── api/                # (예정) REST API 엔드포인트
├── graph/              # (예정) LangGraph 기반 노드 오케스트레이션
├── config/             # (예정) 설정 관리
├── tests/              # (예정) 합의 로직 테스트
├── Dockerfile
├── requirements.txt
└── README.md
```

> 현재는 **Phase 0 데모** 단계입니다. `api/`, `graph/`, `config/`, `tests/` 디렉터리는
> 구조만 잡혀 있으며 구현은 진행 중입니다.

---

## 설정

환경 변수로 동작을 조정할 수 있습니다.

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `CONSENSUS_THRESHOLD` | `2` | 합의로 인정하는 최소 득표 수 |

LLM 모델·온도·Ollama 주소는 현재 `core/nodes.py` 내에서 설정합니다
(`model="llama3.1"`, `temperature=0.3`, `base_url="http://localhost:11434"`).

---

## 동작 원리

```
                          상황 입력
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
                   검증 노드 가중 거부권 검사
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
               합의 도달            불일치 / 저신뢰
                  │                     │
                  ▼                     ▼
              결과 반환            🚨 인간 개입 요청
                  │
                  ▼
            감사 로그 기록 (JSONL)
```

세 노드는 `ThreadPoolExecutor`로 병렬 추론되어 응답 지연을 줄입니다.

---

## 라이선스

(라이선스 미지정 — 필요 시 추가 예정)