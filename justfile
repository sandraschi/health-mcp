set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

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
