# Dockerfile for running the Grafana AI Data Driven MCP server
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ADDRESS=0.0.0.0:8000 \
    LOG_LEVEL=INFO \
    BASE_PATH=/ \
    TRANSPORT=streamable-http

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY app ./app
COPY README.md ./README.md

EXPOSE 8000

CMD ["sh", "-c", "python -m app --address ${APP_ADDRESS} --base-path ${BASE_PATH} --log-level ${LOG_LEVEL} --transport ${TRANSPORT}"]
