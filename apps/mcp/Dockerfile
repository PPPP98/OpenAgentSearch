FROM python:3.12-slim

ENV UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev

COPY app /app/app

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "app.main"]
