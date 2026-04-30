# Repository Guidelines

## Project Structure & Module Organization
Root documentation lives in `README.md` and `CLAUDE.md`. The application code is under `cli_scanner/`:

- `scanner.py`: CLI entrypoint, argument parsing, console output, webhook dispatch.
- `core/`: scanning and analysis logic (`scanner.py`, `analyzer.py`, `yfinance_cookie_patch.py`).
- `utils/`: logging and Discord webhook helpers.
- `run.sh`, `run_discord.sh`, `unix_setup.sh`, `win_setup.bat`: local runner and setup scripts.
- `.github/workflows/earnings_edge.yaml`: weekday scheduled run for Discord output.

Logs are written to `cli_scanner/logs/` at runtime.

## Build, Test, and Development Commands
Work from `cli_scanner/` unless you are editing workflow or repo-level docs.

- `python -m venv venv && source venv/bin/activate`: create and activate the local environment.
- `pip install -r requirements.txt`: install Python dependencies.
- `chmod +x run.sh && ./run.sh`: run the scanner with auto-selected worker count.
- `./run.sh 04/20/2025`: run against a specific earnings date.
- `./run.sh -a AAPL -i`: inspect one ticker and include iron fly output.
- `bash run_discord.sh`: send results to Discord using `.env` or exported secrets.

## Coding Style & Naming Conventions
Follow existing Python style: 4-space indentation, snake_case for functions and variables, PascalCase for classes such as `EarningsScanner` and `OptionsAnalyzer`. Keep modules focused by layer: CLI in `scanner.py`, orchestration in `core/scanner.py`, calculations in `core/analyzer.py`, helpers in `utils/`. Preserve short docstrings and targeted logging rather than adding large comment blocks.

## Testing Guidelines
There is no dedicated `tests/` directory yet. Before opening a PR, run the relevant CLI path you changed, for example `./run.sh -a AAPL` or `python scanner.py --date "04/20/2025" --parallel 0`. Prefer small, deterministic changes and verify both terminal output and log behavior. If you add automated tests, place them in a new `tests/` package and use `test_*.py` naming.

## Commit & Pull Request Guidelines
Recent history mixes concise fixes and feature-style subjects (`Fix: Minor typo`, `Feat: Added OS-specific setup...`). Use short, imperative commit messages and keep each commit scoped to one change. PRs should include the user-visible effect, any required env vars or secrets, sample commands used for validation, and screenshots only if output formatting changed.

## Security & Configuration Tips
Do not commit `.env`, webhook URLs, or API keys. `DISCORD_WEBHOOK_URL` and `FINNHUB_API_KEY` should be provided through local environment variables or GitHub Actions secrets.
