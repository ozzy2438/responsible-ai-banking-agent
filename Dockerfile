FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY pyproject.toml README.md ./
COPY policies ./policies
COPY src ./src
RUN python -m pip install --prefix=/install .

FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/usr/local/bin:$PATH

RUN apt-get update \
    && apt-get upgrade --yes --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 banking \
    && useradd --uid 10001 --gid banking --no-create-home --shell /usr/sbin/nologin banking

COPY --from=builder /install /usr/local
WORKDIR /app
COPY --chown=banking:banking policies ./policies
COPY --chown=banking:banking migrations ./migrations
RUN mkdir -p /app/.local && chown banking:banking /app/.local

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]

CMD ["uvicorn", "responsible_banking_agent.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
