FROM python:3.12-slim

# 필수 패키지 설치 + Git 포함 + 캐시 정리
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-venv \
    git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 로케일 설정 (UTF-8 환경)
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt만 먼저 복사하여 캐시 분리
COPY requirements.txt ./

# 가상환경 생성 및 패키지 설치
RUN python -m venv .venv && \
    . .venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# 나머지 코드 복사
COPY . .

# 가상환경을 PATH에 등록
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 기본 쉘 진입
CMD ["bash"]
