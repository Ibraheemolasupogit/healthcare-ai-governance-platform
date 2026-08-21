# Minimal local development image for the governance platform foundation.
#
# This image exists to give local development and test execution a
# reproducible environment. It is NOT a deployment artifact and does not
# run any service — it drops into a shell with the project installed in
# editable mode so `pytest` / `ruff` behave identically to a host venv.

FROM python:3.12-slim AS dev

# Avoid .pyc files and enable unbuffered stdout for readable logs/test output.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

# Create a non-root user for local development.
RUN useradd --create-home --shell /bin/bash dev

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install -e ".[dev]"

COPY . .

RUN chown -R dev:dev /workspace
USER dev

CMD ["bash"]
