#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repository_root}"

temporary_root="${TMPDIR:-/tmp}"
validation_root="$(mktemp -d "${temporary_root%/}/demo-bmad-validation.XXXXXX")"
trap 'rm -rf "${validation_root}"' EXIT

for variable in $(compgen -e); do
  case "${variable}" in
    AWS_* | CHECKOV_* | MYPY_* | PYTEST_* | RUFF_* | TF_CLI_ARGS* | TF_VAR_* | PYTHONPATH | VIRTUAL_ENV)
      unset "${variable}"
      ;;
  esac
done

export AWS_CONFIG_FILE=/dev/null
export AWS_EC2_METADATA_DISABLED=true
export AWS_SHARED_CREDENTIALS_FILE=/dev/null
export UV_CACHE_DIR="${validation_root}/uv-cache"
export UV_PROJECT_ENVIRONMENT="${validation_root}/venv"
export VALIDATION_TEMP_ROOT="${validation_root}"
export PYTHONDONTWRITEBYTECODE=1

uv lock --check
uv sync --locked
uv run --locked python scripts/validate.py
