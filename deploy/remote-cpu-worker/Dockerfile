FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN useradd --create-home --uid 10001 nexusworker
WORKDIR /app

COPY scripts/nexus_agent_platform/requirements-evidence-ingestion.txt /tmp/requirements-evidence-ingestion.txt
RUN pip install --no-cache-dir -r /tmp/requirements-evidence-ingestion.txt \
    && python -m playwright install --with-deps chromium \
    && chown -R nexusworker:nexusworker /ms-playwright

COPY scripts/nexus_agent_platform /app/scripts/nexus_agent_platform
RUN mkdir -p /app/data/runtime/evidence_ingestion /app/reports/runtime \
    && chown -R nexusworker:nexusworker /app

USER nexusworker
EXPOSE 8787
ENTRYPOINT ["python", "-m", "scripts.nexus_agent_platform.remote_worker", "--serve", "--bind", "0.0.0.0", "--port", "8787", "--provider", "linux-container"]
