## .justfile for managing python dev tasks
# Inspired by this informative article: https://lukasatkinson.de/2025/just-dont-tox/

## Globals/env 
set dotenv-load := true
dotenv-filename := "_local/.env"

PYTHON_RUNTIME := `echo python$(cat .python-version)`
REPO := `basename "$PWD" | tr ' ' '_'`
VENDOR_DIR := "libs/"
DEPRECATED := "deprecated/"

## Commands 
set shell := ['uv', 'run', 'bash', '-euxo', 'pipefail', '-c']
set positional-arguments 

qa *args: deps lint type_src (test) cov

deps: 
    deptry -e .venv/ -e deprecated/ -e libs/ -e docs/ -e tests/ .

compose: 
    docker compose up -d 

cov: 
    coverage html

test *args:
    coverage run -m pytest -q -s \
      --ignore={%raw%}{{VENDOR_DIR}}{%endraw%} \
      tests/ "$@"

lint *args:
    ruff check "$@"

type *args:
    mypy "$@"

type_app: 
    mypy app.py 

type_utils: 
    mypy utils/

type_src: 
    mypy SRC

toml_req: 
    uv pip compile --group test pyproject.toml -o requirements.txt

py312 *args: 
    #!/bin/sh
    uv run --isolated --python=3.12 pytest -q -s \
      --ignore={%raw%}{{VENDOR_DIR}}{%endraw%} \
      tests/ "$@"

py311 *args: 
    #!/bin/sh
    uv run --isolated --python=3.11 pytest -q -s \
      --ignore={%raw%}{{VENDOR_DIR}}{%endraw%} \
      tests/ "$@"

py310 *args: 
    #!/bin/sh
    uv run --isolated --python=3.10 pytest -q -s \
      --ignore={%raw%}{{VENDOR_DIR}}{%endraw%} \
      tests/ "$@"

py_requirements *args: 
    toml_req
    
    #!/usr/bin/env bash
    set -euo pipefail

    PY="{%raw%}{{PYTHON_RUNTIME}}{%endraw%}"

    TMP_DIR="$(mktemp -d -t venvreq.XXXXXX)"
    VENV_DIR="$TMP_DIR/venv"

    "$PY" -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"

    # Use pip from this venv
    python -m pip install --upgrade pip wheel
    python -m pip install -r requirements.txt

    # Run tests
    pytest -q -s \
      --ignore={%raw%}{{VENDOR_DIR}}{%endraw%} \
      tests/ "$@"

    deactivate
    rm -rf "$TMP_DIR"

