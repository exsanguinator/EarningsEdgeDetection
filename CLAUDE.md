# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

All commands run from the `cli_scanner/` directory with the venv active:

```bash
cd cli_scanner
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install yahooquery webdriver-manager
```

Google Chrome must be installed (used for headless scraping of Market Chameleon).

## Running the Scanner

```bash
# From cli_scanner/
chmod +x ./run.sh
./run.sh                          # current date, auto-detect workers
./run.sh 04/20/2025               # specific date
./run.sh -l                       # compact list output
./run.sh -i                       # include iron fly calculations
./run.sh -a AAPL                  # analyze a single ticker
./run.sh -a AAPL -i               # single ticker with iron fly
./run.sh -c                       # use all earnings sources combined

# Manually with custom worker count
python scanner.py --date "04/20/2025" --parallel 4

# Discord output (reads DISCORD_WEBHOOK_URL from .env)
bash run_discord.sh
```

Optional env vars: `FINNHUB_API_KEY` (for Finnhub source), `DISCORD_WEBHOOK_URL`.

## Architecture

The codebase has three layers:

**CLI layer** (`scanner.py`): Parses arguments, formats console output, sends Discord webhooks via `utils/discord_webhook.py`. The `--forever` flag loops indefinitely.

**Scanner layer** (`core/scanner.py`, `EarningsScanner`):
- `get_scan_dates()`: Time-based logic — before 4 PM ET scans today post-market + tomorrow pre-market; after 4 PM scans tomorrow post-market + day-after pre-market. Handles Friday→Monday weekend skip.
- `fetch_earnings_data()`: Selects data source based on flags. Default: Investing.com with Finnhub fallback. `-u`: DoltHub + Finnhub. `-c`: all three merged (DoltHub preferred for timing).
- `validate_stock()`: Ordered filter chain — price → options/expiry → open interest → core analysis → term structure (hard exit at > -0.004) → ATM delta → expected move → volume → Market Chameleon winrate → IV/RV. Returns tier 1/2/near-miss/skip.
- `adjust_thresholds_based_on_spy()`: Dynamically relaxes IV/RV thresholds when SPY IV/RV is low (four tiers down to 0.75).
- `check_mc_overestimate()`: Selenium scrape of Market Chameleon; single shared browser instance with thread lock and retry.
- `scan_earnings()`: Orchestrates parallel or batched processing. Parallel mode caps at 8 workers.

**Analyzer layer** (`core/analyzer.py`, `OptionsAnalyzer`):
- `compute_recommendation()`: Fetches options chains for dates 45+ days out, calculates ATM IV per expiry, builds a linear interpolation term structure, extracts IV at 30 DTE, computes term slope, Yang-Zhang realized vol (30-day), and returns IV/RV ratio. Straddle price from the nearest expiry gives expected move.
- `yang_zhang_volatility()`: OHLC-based volatility estimator; falls back to close-to-close if it errors.

**Patching** (`core/yfinance_cookie_patch.py`): Patches yfinance cookie handling; applied at module import time in `core/scanner.py`. The `curl_cffi` session impersonating Chrome is shared globally.

## Tier Logic

- **Tier 1**: All hard filters pass, no near-miss criteria.
- **Tier 2**: All hard filters pass, ≥1 near-miss criteria failure, term structure ≤ -0.006.
- **Near miss**: All hard filters pass, near-miss criteria failures, term structure between -0.006 and -0.004.
- **Skip**: Any hard filter fails (price, expiry ≤ 9 days, OI, term structure, delta, expected move).

## GitHub Actions

Workflow (`.github/workflows/earnings_edge.yaml`) runs at 9:57 AM ET weekdays, installs deps, and calls `run_discord.sh`. Secrets needed: `DISCORD_WEBHOOK_URL`, `FINNHUB_API_KEY`.

> **Keepalive**: GitHub auto-disables scheduled workflows after 60 days of repository inactivity. `keep-alive.sh` automates this — run it manually or on a schedule to commit a timestamp bump and keep the workflow active. Commit something to the repo at least every 60 days to keep the daily scan running.

## Logs

Each run writes a dated log file to `cli_scanner/logs/`.
