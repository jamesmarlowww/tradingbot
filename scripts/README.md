# Trading Bot System

## Bot Hierarchy

### Main Bots (`scripts/bots/`)

1. **monitorBot.py** - Strategy Monitor & Analyzer
   - Analyzes all trading combinations (504 total)
   - Identifies successful strategies based on performance
   - Saves results to BigQuery for tracking
   - **Usage**: `python scripts/bots/monitorBot.py`

2. **testTradingBot.py** - Live Testing Bot
   - Runs live trading on successful combinations from monitorBot
   - Uses streak-based automation (requires 5 consecutive positive days)
   - Polls API every 15 minutes for live data
   - **Usage**: `python scripts/bots/testTradingBot.py`

3. **backTestBot.py** - Historical Backtesting
   - Runs historical backtests on past data (last 30 days)
   - Validates strategy performance
   - **Usage**: `python scripts/bots/backTestBot.py`

4. **prodTradingBot.py** - Production Trading
   - Live trading with real money
   - Uses proven strategies from testTradingBot
   - **Usage**: `python scripts/bots/prodTradingBot.py`

### Helper Scripts (`scripts/helpers/`)

**Testing & Validation:**
- **test_*.py** - Testing and validation scripts
- **check_*.py** - Data verification scripts

**Trade Management:**
- **manage_*.py** - Trade management and analysis
- **trade_utils.py** - Trade utility functions
- **performance_utils.py** - Performance analysis utilities

**Data Management:**
- **migrate_*.py** - Data migration scripts
- **reset_*.py** - Database reset scripts
- **data_processing.py** - Data processing utilities
- **backtest_utils.py** - Backtesting utilities

**Reporting & Visualization:**
- **create_performance_graphs.py** - Performance graph generation
- **upload_to_sheets.py** - Google Sheets upload utilities

**Utilities:**
- **add_testnet_funds.py** - Testnet fund management
- **show_bot_combinations.py** - Display bot combinations
- **run_bot_system.py** - Bot system runner
- **smart_backtest.py** - Advanced backtesting

### Core Utilities (`utils/`)

**Core Bot Functionality:**
- **bot_core.py** - Shared bot core functionality
- **database.py** - Database interface
- **bigquery_database.py** - BigQuery interface
- **postgres_database.py** - PostgreSQL interface

## Workflow

### 1. Strategy Analysis
```bash
python scripts/bots/monitorBot.py
```
- Analyzes all 504 trading combinations
- Identifies successful strategies
- Saves results to BigQuery

### 2. Live Testing
```bash
python scripts/bots/testTradingBot.py
```
- Runs live trading on successful combinations
- Uses streak-based automation (5 consecutive positive days)
- Polls API every 15 minutes

### 3. Historical Validation
```bash
python scripts/bots/backTestBot.py
```
- Runs historical backtests on past data
- Validates strategy performance

### 4. Production Trading
```bash
python scripts/bots/prodTradingBot.py
```
- Live trading with real money
- Uses proven strategies from testTradingBot

## Configuration

- **Automation**: `config/automation_config.py` - Controls streak-based trading
- **API Keys**: `config/config.py` - Binance API configuration
- **Emergency Override**: Set `EMERGENCY_OVERRIDE = True` to force trading enabled

## Key Features

- **Streak-based Automation**: Requires 5 consecutive positive days before trading
- **Live Data Polling**: 15-minute intervals for real-time market analysis
- **BigQuery Integration**: Stores all trade data and performance metrics
- **Risk Management**: 2% stop loss, 6% take profit, 5% max position size
