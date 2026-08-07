set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

default:
    @just --list

install:
    uv sync

run:
    uv run health-mcp

serve: run

test:
    uv run pytest

lint:
    uv run ruff check src/

fix:
    uv run ruff check --fix src/
    uv run ruff format src/

pack:
    mcpb pack . dist/health-mcp.mcpb

# Bootstrap: install dev deps + pre-commit hook
bootstrap:
    uv sync --group dev
    uv run pre-commit install
    Write-Host "Pre-commit hooks installed." -ForegroundColor Green