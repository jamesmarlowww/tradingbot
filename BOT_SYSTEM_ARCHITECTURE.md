# Complete Bot System Architecture

## Overview

This document explains the complete trading bot system architecture that maximizes code reuse across backTestBot, testBot, and prodBot while implementing intelligent streak-based automation.

## System Components

### 1. Shared Core (`utils/bot_core.py`)
**Purpose**: Centralized logic shared across all bots

**Key Features**:
- Strategy management and instantiation
- Market data fetching and indicator calculation
- Streak-based automation logic
- BigQuery integration for trade storage
- Performance metrics calculation
- Daily monitoring capabilities

**Shared Functions**:
- `get_strategy_instance()` - Creates strategy objects with default parameters
- `fetch_market_data()` - Gets market data for any symbol/timeframe
- `calculate_indicators()` - Calculates technical indicators
- `generate_signals()` - Generates trading signals
- `check_streak_conditions()` - Implements 5-day streak logic
- `save_trade_to_bigquery()` - Saves completed trades
- `calculate_performance_metrics()` - Calculates comprehensive metrics
- `run_daily_monitor()` - Runs continuous market monitoring

### 2. Daily Monitor (backTestBot in monitor mode)
**Purpose**: Continuously monitors market conditions and builds streak data

**How it works**:
```bash
# Run daily monitor (checks every hour)
python scripts/backTestBot.py --mode monitor --monitor-interval 3600

# Monitor specific combinations
python scripts/backTestBot.py --mode monitor --combinations ETHUSDT:EnhancedRSIStrategy:4h SOLUSDT:TrendFollowingStrategy:1h
```

**What it does**:
- Runs continuously in the background
- Analyzes all trading combinations hourly
- Records market analysis to BigQuery
- Builds historical streak data
- Does NOT execute actual trades
- Provides data for streak analysis

### 3. Test Bot (testTradingBot)
**Purpose**: Executes trades only when 5+ day positive streaks are detected

**How it works**:
```bash
# Run test bot (automatically checks streak conditions)
python scripts/testTradingBot.py
```

**What it does**:
- Checks streak conditions daily
- Only trades when 5+ consecutive positive days detected
- Saves completed trades to BigQuery
- Uses shared core for all logic
- Runs on testnet for safety

### 4. Production Bot (prodTradingBot)
**Purpose**: Production trading with additional safety measures

**How it works**:
```bash
# Run production bot (when conditions are met)
python scripts/prodTradingBot.py
```

**What it does**:
- Same logic as test bot but with real money
- Additional risk management
- Production API keys
- More conservative position sizing

### 5. System Controller (run_bot_system.py)
**Purpose**: Orchestrates the entire system

**How it works**:
```bash
# Run intelligent controller (recommended)
python scripts/run_bot_system.py --mode control

# Run individual components
python scripts/run_bot_system.py --mode monitor
python scripts/run_bot_system.py --mode test
python scripts/run_bot_system.py --mode prod
python scripts/run_bot_system.py --mode all
```

**What it does**:
- Monitors streak conditions continuously
- Automatically starts/stops bots based on conditions
- Manages all bot processes
- Provides system-wide logging

## Data Flow

### 1. Daily Monitoring Flow
```
backTestBot (monitor mode) 
    ↓ (hourly)
Market Analysis → BigQuery (daily_summary table)
    ↓ (daily)
Streak Analysis → Automation Decision
```

### 2. Trading Flow
```
Streak Conditions Met (5+ positive days)
    ↓
Test Bot Starts
    ↓
Market Analysis → Signal Generation → Trade Execution
    ↓
Trade Results → BigQuery (trades table)
    ↓
Updated Streak Data
```

### 3. Streak Analysis Flow
```
BigQuery (trades table)
    ↓
Daily Profit Calculation (last 5 days)
    ↓
Positive Days Count
    ↓
Trading Decision (≥5 days = ENABLE, <5 days = DISABLE)
```

## Configuration

### Automation Settings (`config/automation_config.py`)
```python
STREAK_AUTOMATION_ENABLED = True
REQUIRED_POSITIVE_DAYS = 5
MIN_PROFIT_THRESHOLD = 0.0
AUTOMATION_CHECK_INTERVAL = 24 * 60 * 60  # 24 hours
EMERGENCY_OVERRIDE = False
```

### Trading Combinations
**backTestBot**: 100+ combinations for comprehensive testing
**testBot**: 3 focused combinations (ETHUSDT, SOLUSDT, LINKUSDT)
**prodBot**: Same as testBot but with real money

## Usage Examples

### 1. Start Daily Monitoring
```bash
# Start continuous market monitoring
python scripts/backTestBot.py --mode monitor --monitor-interval 3600
```

### 2. Run Complete System
```bash
# Start intelligent controller (recommended)
python scripts/run_bot_system.py --mode control
```

### 3. Manual Testing
```bash
# Test streak analysis
python scripts/test_bigquery_streak.py

# Test automation logic
python scripts/test_automation.py
```

### 4. Individual Bot Testing
```bash
# Test bot only
python scripts/testTradingBot.py

# Production bot only
python scripts/prodTradingBot.py
```

## Code Reuse Benefits

### 1. Shared Logic
- **Strategy Management**: All bots use same strategy instantiation
- **Market Data**: Unified data fetching and indicator calculation
- **Streak Analysis**: Same 5-day streak logic across all bots
- **BigQuery Integration**: Consistent data storage and retrieval
- **Performance Metrics**: Same calculation methods

### 2. Configuration Sharing
- **Strategy Parameters**: Default parameters defined once
- **Automation Settings**: Centralized configuration
- **Risk Management**: Shared position sizing and risk rules

### 3. Maintenance Benefits
- **Single Point of Update**: Changes to core logic affect all bots
- **Consistent Behavior**: All bots behave predictably
- **Easier Testing**: Test core logic once, works everywhere
- **Reduced Bugs**: Less duplicate code = fewer bugs

## Monitoring and Logging

### Log Files
- `data/logs/trading_bot.log` - Test bot logs
- `data/logs/bot_system.log` - System controller logs
- `data/logs/backtest_bot.log` - Backtest bot logs

### BigQuery Tables
- `trades` - Completed trade records
- `daily_summary` - Market analysis records
- `performance_metrics` - Calculated performance data

### Key Metrics Tracked
- Daily profit/loss
- Streak counts (positive days)
- Trading decisions (enabled/disabled)
- Performance metrics (win rate, drawdown, Sharpe ratio)

## Safety Features

### 1. Emergency Override
```python
EMERGENCY_OVERRIDE = True  # Force trading enabled
```

### 2. Testnet Usage
- Test bot uses testnet by default
- Production bot requires explicit configuration

### 3. Position Limits
- Maximum 5% of balance per position
- 2% stop loss, 6% take profit
- Maximum 1% risk per trade

### 4. Process Management
- Automatic bot start/stop based on conditions
- Graceful shutdown handling
- Process monitoring and restart

## Troubleshooting

### Common Issues
1. **No streak data**: Ensure daily monitor is running
2. **BigQuery errors**: Check credentials and permissions
3. **Bot not trading**: Check streak conditions and automation settings
4. **Performance issues**: Monitor system resources and API limits

### Debug Commands
```bash
# Check BigQuery connection
python scripts/test_bigquery.py

# Test streak analysis
python scripts/test_bigquery_streak.py

# Verify automation logic
python scripts/test_automation.py

# Check trade data
python scripts/compare_trades_csv_bigquery.py
```

## Future Enhancements

### 1. Advanced Streak Analysis
- Multiple timeframe streaks
- Volume-weighted streaks
- Market condition filtering

### 2. Machine Learning Integration
- Predictive streak modeling
- Dynamic parameter adjustment
- Risk assessment algorithms

### 3. Enhanced Monitoring
- Real-time dashboard
- Email/SMS notifications
- Performance alerts

### 4. Portfolio Management
- Multi-asset allocation
- Correlation analysis
- Risk parity strategies

## Conclusion

This architecture provides:
- **Maximum code reuse** across all bots
- **Intelligent automation** based on proven 5-day streaks
- **Continuous monitoring** for market conditions
- **Scalable design** for future enhancements
- **Safety features** for risk management

The system automatically adapts to market conditions while maintaining consistent behavior across all components. 