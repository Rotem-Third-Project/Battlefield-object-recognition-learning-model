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