FROM python:3.12-slim

WORKDIR /app
ARG INSTALL_WHISPER=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && ffmpeg -version \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY requirements-whisper.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN if [ "$INSTALL_WHISPER" = "true" ]; then pip install --no-cache-dir -r requirements-whisper.txt; fi

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=3).read()"

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
