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
