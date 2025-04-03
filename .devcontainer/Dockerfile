FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-venv \
    && apt-get clean

WORKDIR /app

# requirements.txt만 먼저 복사해서 캐시 분리
COPY requirements.txt ./
RUN python -m venv .venv \
    && . .venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

CMD [ "bash" ]