# Ollama 서버 상태 및 모델 가용성 조회
# dashboard에서 "현재 어떤 모델이 활성화되어 있는가"를 표시하기 위한 헬퍼.

from typing import Optional
from pydantic import BaseModel
import requests

from core.nodes import LLM_MODEL, LLM_BASE_URL, LLM_TEMPERATURE


class ModelHealth(BaseModel):
    configured_model: str       # core/nodes.py가 사용하도록 설정된 모델명
    base_url: str
    temperature: float
    server_reachable: bool      # Ollama 서버 응답 여부
    model_available: bool       # 설정된 모델이 실제 받아져 있는지
    installed_models: list[str] # 받아져 있는 모델 전체 목록
    status_message: str         # 사용자에게 보여줄 한 줄 메시지
    status_level: str           # "ok" | "warning" | "error"


def check_ollama() -> ModelHealth:
    """Ollama /api/tags를 호출해서 서버 상태와 모델 가용성을 확인한다."""
    try:
        resp = requests.get(f"{LLM_BASE_URL}/api/tags", timeout=2.0)
        resp.raise_for_status()
        data = resp.json()
        # Ollama 응답 형식: {"models": [{"name": "llama3.1:latest", "model": "llama3.1:latest", ...}, ...]}
        installed = [m.get("name", "") for m in data.get("models", [])]
        # tag 비교: 설정값이 "llama3.1"이고 설치된 게 "llama3.1:latest"여도 매칭으로 본다
        configured = LLM_MODEL
        model_available = any(
            name == configured or name.split(":")[0] == configured.split(":")[0]
            for name in installed
        )

        if model_available:
            return ModelHealth(
                configured_model=configured,
                base_url=LLM_BASE_URL,
                temperature=LLM_TEMPERATURE,
                server_reachable=True,
                model_available=True,
                installed_models=installed,
                status_message=f"모델 `{configured}` 활성 — Ollama 응답 정상",
                status_level="ok",
            )
        else:
            return ModelHealth(
                configured_model=configured,
                base_url=LLM_BASE_URL,
                temperature=LLM_TEMPERATURE,
                server_reachable=True,
                model_available=False,
                installed_models=installed,
                status_message=(
                    f"⚠ 모델 `{configured}`이 설치되어 있지 않습니다. "
                    f"`ollama pull {configured}` 또는 ENTELECHSCOPE_MODEL 환경변수로 다른 모델을 지정하세요."
                ),
                status_level="warning",
            )

    except requests.exceptions.ConnectionError:
        return ModelHealth(
            configured_model=LLM_MODEL,
            base_url=LLM_BASE_URL,
            temperature=LLM_TEMPERATURE,
            server_reachable=False,
            model_available=False,
            installed_models=[],
            status_message=(
                f"✗ Ollama 서버에 연결할 수 없습니다 ({LLM_BASE_URL}). "
                f"`ollama serve`로 서버를 먼저 실행하세요."
            ),
            status_level="error",
        )
    except Exception as e:
        return ModelHealth(
            configured_model=LLM_MODEL,
            base_url=LLM_BASE_URL,
            temperature=LLM_TEMPERATURE,
            server_reachable=False,
            model_available=False,
            installed_models=[],
            status_message=f"✗ Ollama 상태 조회 실패: {str(e)[:100]}",
            status_level="error",
        )