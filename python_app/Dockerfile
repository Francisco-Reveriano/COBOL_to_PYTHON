# syntax=docker/dockerfile:1.7
# Multi-stage build for the CBSA Python service.
# Stage 1 installs Python dependencies into an isolated user prefix so the
# runtime image stays lean and only contains what is needed to run uvicorn.

ARG PYTHON_IMAGE=python:3.12.7-slim-bookworm

# ---------- builder ----------
FROM ${PYTHON_IMAGE} AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

COPY requirements.txt ./
RUN pip install --user -r requirements.txt

# ---------- runtime ----------
FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# curl is needed for the HEALTHCHECK; ca-certificates is good hygiene for TLS.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user matching the spec (uid 1000, name cbsa).
RUN groupadd --system --gid 1000 cbsa \
    && useradd --system --uid 1000 --gid cbsa --create-home --home-dir /home/cbsa --shell /usr/sbin/nologin cbsa

# Copy the pip --user install tree from the builder into the cbsa user's home
# and expose it on PATH so console scripts like `uvicorn` and `alembic` resolve.
COPY --from=builder --chown=cbsa:cbsa /root/.local /home/cbsa/.local
ENV PATH=/home/cbsa/.local/bin:$PATH \
    PYTHONPATH=/app

WORKDIR /app
COPY --chown=cbsa:cbsa app ./app
COPY --chown=cbsa:cbsa alembic ./alembic
COPY --chown=cbsa:cbsa alembic.ini ./alembic.ini

USER cbsa

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
