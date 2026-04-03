FROM ubuntu:24.04

# ----- 기본 설정 -----
ARG DEBIAN_FRONTEND=noninteractive
ARG PROJECT_NAME
ENV TZ=Asia/Seoul
ENV SHELL=/bin/bash

# ----- APT 미러 교체 및 필수 도구 설치 -----
# 수정됨: Ubuntu 24.04에 맞게 ubuntu.sources 파일 수정 및 python3-venv 추가
RUN sed -i 's|http://archive.ubuntu.com|http://mirror.navercorp.com|g' /etc/apt/sources.list.d/ubuntu.sources && \
    sed -i 's|http://security.ubuntu.com|http://mirror.navercorp.com|g' /etc/apt/sources.list.d/ubuntu.sources && \
    apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
      build-essential wget curl git sudo locales tzdata vim nano less zip unzip tar gzip net-tools lsof \
      python3 python3-pip python3-venv ca-certificates gnupg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ----- Node.js & npm 설치 (NodeSource 공식 LTS) -----
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ----- 사용자 defuser 생성 및 sudo 권한 부여 -----
RUN useradd -m -s /bin/bash defuser && \
    echo "defuser:defuser" | chpasswd && usermod -aG sudo defuser

# ----- Miniconda 설치 -----
# 수정됨: defuser가 conda를 사용할 수 있도록 폴더 소유권 변경
RUN wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/conda && rm /tmp/miniconda.sh && \
    ln -s /opt/conda/bin/conda /usr/local/bin/conda && \
    chown -R defuser:defuser /opt/conda && \
    echo 'export PATH="/opt/conda/bin:$PATH"' >> /home/defuser/.bashrc && \
    sudo -u defuser /opt/conda/bin/conda clean -afy

# ----- defuser 전환 -----
USER defuser
WORKDIR /home/defuser/${PROJECT_NAME}

# ----- Poetry 설치 -----
# 수정됨: 계정 전환 후 설치하여 defuser의 홈 디렉터리에 정상적으로 들어가게 함
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    echo 'export PATH="/home/defuser/.local/bin:$PATH"' >> /home/defuser/.bashrc

# ----- Node, Python, Poetry 버전 점검 -----
# 수정됨: RUN 단계에서는 임시로 전체 경로를 지정하여 확인
RUN node -v && npm -v && python3 --version && \
    /home/defuser/.local/bin/poetry --version

# ----- 기본 CMD -----
CMD ["/bin/bash"]
