# EarningsEdgeDetection Project Context

## Project Overview
EarningsEdgeDetection is a sophisticated options scanning tool designed to identify high-probability trade setups around earnings announcements. It focuses on volatility term structure analysis, historical win rates, and liquidity metrics to categorize trades into three tiers: Recommended (Tier 1 & 2) and Near Misses.

The project is primarily written in Python and leverages various financial data sources and web scraping techniques to gather real-time market data.

### Key Technologies
- **Python 3.x**: Core programming language.
- **Financial Data APIs**: `yfinance`, `yahooquery`, `Finnhub`, `DoltHub` (via MySQL connector).
- **Web Scraping/Automation**: `Selenium` (headless Chrome), `curl_cffi`, `BeautifulSoup4`.
- **Data Analysis**: `pandas`, `numpy`, `scipy` (for Yang-Zhang volatility and IV term structure interpolation).
- **Concurrency**: `ThreadPoolExecutor` for parallelizing stock analysis.
- **Notifications**: Discord Webhooks integration.

## Project Structure
The project is organized into a core scanner module and utility functions:

- `cli_scanner/scanner.py`: The main entry point for the CLI application. Handles argument parsing and orchestrates the scanning process.
- `cli_scanner/core/scanner.py`: Contains the `EarningsScanner` class, responsible for fetching earnings calendars, retrieving stock/options data, and managing the parallel execution of analyses.
- `cli_scanner/core/analyzer.py`: Contains the `OptionsAnalyzer` class, which implements the mathematical models for volatility (Yang-Zhang), term structure analysis, and the multi-tier filtering logic.
- `cli_scanner/core/yfinance_cookie_patch.py`: A utility to handle cookie-based authentication for Yahoo Finance.
- `cli_scanner/utils/`:
    - `logging_utils.py`: Standardized logging configuration.
    - `discord_webhook.py`: Logic for sending results to Discord.
- `cli_scanner/run.sh`: A shell script for easy execution with automatic thread detection.

## Building and Running

### Setup
1. Navigate to the `cli_scanner` directory.
2. Install dependencies: `pip install -r requirements.txt`.
3. (Optional) Install `dolt` and setup the earnings database for enhanced data sources.
4. Set `FINNHUB_API_KEY` environment variable if using Finnhub.

### Key Commands
- **Standard Scan**: `./run.sh` (Auto-detects date and threads).
- **Manual Scan with Parallelism**: `python scanner.py -p 8`.
- **Specific Date Scan**: `python scanner.py --date "MM/DD/YYYY"`.
- **Analyze Single Ticker**: `python scanner.py --analyze TICKER`.
- **Iron Fly Analysis**: `python scanner.py --iron-fly`.
- **Combined Sources**: `python scanner.py --all-sources`.

## Development Conventions

### Coding Style
- **Modular Design**: Logic is separated into scanning (data retrieval) and analysis (mathematical modeling).
- **Typing**: Uses Python type hints for improved clarity and error catching.
- **Logging**: Extensive logging to both console and `logs/` directory. Each run generates a unique log file.
- **Error Handling**: Graceful fallbacks for data sources (e.g., falling back to simple volatility if Yang-Zhang fails, or using Yahoo Finance if Investing.com is blocked).

### Filtering Criteria
The scanner enforces strict "Hard Filters":
- Stock Price >= $10.00
- Options Expiration <= 9 days
- Open Interest >= 2,000 contracts
- Term Structure <= -0.004
- Expected Move >= $0.90

### Trade Categorization
- **Tier 1**: Meets all core and additional criteria (Volume, Winrate, IV/RV ratio).
- **Tier 2**: One minor failure but maintains strong term structure (<= -0.006).
- **Near Misses**: Good setups that fail one or two secondary filters but maintain the hard filters.
