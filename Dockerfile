# Stage 1: install dependencies and build the package
FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# Stage 2: minimal runtime image
FROM python:3.11-slim
WORKDIR /app
RUN useradd --no-create-home --shell /bin/false appuser
COPY --from=builder /app/.venv /app/.venv
COPY src/ /app/src/
ENV PATH="/app/.venv/bin:$PATH"
USER appuser
ENTRYPOINT ["uptime"]
