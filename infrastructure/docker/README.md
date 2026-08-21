# Docker (development foundation)

## Purpose

A minimal, reproducible local development and test environment — not a deployment artifact, and
not a runtime for any live service. Nothing in this platform is deployed via this image.

## What it does

`Dockerfile` builds a Python 3.12 image with the project installed in editable mode
(`pip install -e ".[dev]"`), so `pytest`, `ruff check`, and `ruff format --check` behave the same
inside the container as in a local virtualenv. `docker-compose.yml` mounts the repository into the
container and drops into a shell.

## Usage

```bash
docker compose -f infrastructure/docker/docker-compose.yml run --rm dev

# inside the container
pytest
ruff check .
python scripts/validate_repository.py
```

## Explicitly out of scope here

- No application server, API, or long-running process is defined.
- No Snowflake, Fabric, or other external connection is configured.
- No secrets, credentials, or `.env` files are baked into or expected by this image.
- This is not a production or CI base image; CI ([`.github/workflows/ci.yml`](../../.github/workflows/ci.yml))
  runs directly on GitHub-hosted runners with `actions/setup-python`, not this container.
