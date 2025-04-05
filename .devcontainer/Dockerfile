# ✅ 최신 Python 3.12 slim 이미지 사용
FROM python:3.12-slim

# ✅ 필수 패키지 설치 (venv 포함)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-venv \
    && apt-get clean

# ✅ 작업 디렉토리 설정
WORKDIR /app

# ✅ requirements.txt 복사
COPY requirements.txt ./

# ✅ 가상환경 생성 및 활성화 후 패키지 설치
RUN python -m venv .venv \
    && . .venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

# ✅ 소스코드 복사
COPY . .

# ✅ VS Code가 가상환경을 자동 인식하게 설정
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# ✅ bash로 진입 (VS Code와 연동 위해)
CMD [ "bash" ]

FROM python:3.12-slim

# 필수 패키지 + Node.js + Git 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-venv \
    curl \
    git && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 로케일 설정
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt 먼저 복사 (캐시 활용)
COPY requirements.txt ./

# Python 가상환경 생성 및 의존성 설치
RUN python -m venv .venv && \
    . .venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# 전체 프로젝트 복사
COPY . .

# 가상환경을 기본 PATH로 설정
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 기본 쉘
CMD ["bash"]