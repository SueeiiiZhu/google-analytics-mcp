# Repository Guidelines

## Project Structure & Module Organization
Core code lives in `analytics_mcp/`. `server.py` is the console entry point wired to the `analytics-mcp` script, and `coordinator.py` assembles the MCP app. Tool implementations are grouped under `analytics_mcp/tools/` by domain: `admin/` for account and property metadata, `reporting/` for core, realtime, and metadata reports, and `utils.py` for shared helpers. Tests live in `tests/` and currently follow a small `unittest` layout such as `tests/utils_test.py`.

## Build, Test, and Development Commands
Use the pinned interpreter from this workspace to avoid version drift:

```sh
$PYTHON_BIN -m pip install -e ".[dev]"
nox -s lint
nox -s format
nox -s tests-3.10
nox -s tests-3.13
```

`install -e ".[dev]"` installs the package plus `black` and `nox`. `nox -s lint` checks formatting only. `nox -s format` applies `black` fixes. `nox -s tests-<python>` runs `coverage` with `unittest discover`; `nox -s tests*` runs all supported versions available locally.

## Coding Style & Naming Conventions
Follow PEP 8 with `black` enforcing an 80-character line length. Use 4-space indentation, module docstrings, and explicit imports. Keep module names lowercase with underscores, mirror the existing package layout, and name test files `*_test.py`. Favor small helper functions in `analytics_mcp/tools/` instead of adding logic directly to the server entry point.

## Testing Guidelines
Write unit tests with the standard library `unittest` framework. Place tests under `tests/` and match the discovery pattern used in `noxfile.py`: `*_test.py`. Add coverage for new tool behavior and validation helpers, especially input normalization and API request shaping. Run the narrowest relevant session locally before opening a PR, then run the full `nox -s tests*` matrix when possible.

## Commit & Pull Request Guidelines
Recent history uses Conventional Commit prefixes such as `fix:`, `feat:`, and `chore(deps):`. Keep subjects imperative and scoped when useful, for example `fix: normalize property resource names`. Pull requests should include a short problem statement, the implementation summary, and test evidence. Link related issues, and note any Gemini or MCP manual verification when behavior changes. Google requires CLA signing before contributions can be merged.

## Security & Configuration Tips
Do not commit credentials or local ADC paths. Keep Google Analytics access in local environment variables or your `~/.gemini/settings.json`, and test with least-privilege read-only credentials.

When debugging imports, use the same interpreter for install and runtime. In
this workspace, prefer `/Users/shiwen/.pyenv/versions/codex/bin/python`. If
you hit `ImportError: cannot import name 'admin_v1beta' from 'google.analytics'`,
the usual cause is that `google-analytics-admin` was not installed in the
active environment. Reinstall with `/Users/shiwen/.pyenv/versions/codex/bin/python -m pip install -e ".[dev]"` and avoid Python 3.14+ until compatibility is confirmed.
