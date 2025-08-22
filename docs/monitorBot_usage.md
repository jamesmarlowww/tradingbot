# Monitor Bot Usage Guide

The `monitorBot.py` is a flexible monitoring and trading bot that can run on various schedules and timeframes.

## Overview

The Monitor Bot serves two main purposes:
1. **Daily Monitoring** - Track performance and collect data for streak analysis
2. **Active Trading** - Execute trades based on signals and streak conditions

## Features

- **Multiple Schedule Options**: 15m, 30m, 1h, 2h, 4h, daily, continuous
- **Active Trading Mode**: Can execute trades when streak conditions are met
- **BigQuery Integration**: All data saved with `run_name = 'monitorBot'`
- **Shared BotCore**: Uses the same logic as other bots for consistency
- **Flexible Combinations**: Can monitor specific symbol/strategy/timeframe combinations

## Usage Examples

### 1. Comprehensive Monitoring (Default)
```bash
# Monitor all combinations hourly (comprehensive monitoring)
python scripts/monitorBot.py

# Same as above, explicit
python scripts/monitorBot.py --schedule comprehensive
```

### 2. Timeframe-Specific Monitoring
```bash
# Monitor 15-minute combinations every 15 minutes
python scripts/monitorBot.py --schedule 15m

# Monitor 30-minute combinations every 30 minutes
python scripts/monitorBot.py --schedule 30m

# Monitor hourly combinations every hour
python scripts/monitorBot.py --schedule 1h

# Monitor daily combinations every 24 hours
python scripts/monitorBot.py --schedule daily
```

### 3. Active Trading Mode
```bash
# Active trading with 5-minute intervals (default)
python scripts/monitorBot.py --mode trading

# Active trading with custom interval (10 minutes)
python scripts/monitorBot.py --mode trading --interval 600

# Active trading on 15-minute schedule
python scripts/monitorBot.py --mode trading --schedule 15m
```

### 4. Custom Combinations
```bash
# Monitor specific combinations
python scripts/monitorBot.py --combinations BTCUSDT:RSIStrategy:15m ETHUSDT:EnhancedRSIStrategy:1h

# Active trading on specific combinations
python scripts/monitorBot.py --mode trading --combinations BTCUSDT:RSIStrategy:15m
```

### 5. Custom Intervals
```bash
# Custom monitoring interval (2 hours)
python scripts/monitorBot.py --interval 7200

# Custom trading interval (3 minutes)
python scripts/monitorBot.py --mode trading --interval 180
```

### 6. Custom Run Name
```bash
# Use custom run name for BigQuery
python scripts/monitorBot.py --run-name myMonitorBot
```

## Schedule Configurations

| Schedule | Interval | Description | Best For |
|----------|----------|-------------|----------|
| `15m` | 15 minutes | 15-minute timeframe combinations | Active trading, short-term signals |
| `30m` | 30 minutes | 30-minute timeframe combinations | Swing trading, medium-term analysis |
| `1h` | 1 hour | 1-hour timeframe combinations | Day trading, hourly trends |
| `2h` | 2 hours | 2-hour timeframe combinations | Medium-term trends |
| `4h` | 4 hours | 4-hour timeframe combinations | Long-term trends |
| `daily` | 24 hours | Daily timeframe combinations | Performance tracking, streak analysis |
| `comprehensive` | 1 hour | **ALL combinations** (default) | Complete market coverage, strategy analysis |
| `continuous` | 1 minute | **ALL combinations** continuously | Maximum responsiveness, real-time analysis |

## Comprehensive Monitoring Combinations

The bot monitors **ALL** combinations from the backTestBot by default:

### Symbols Covered
- **BTCUSDT** - Bitcoin
- **ETHUSDT** - Ethereum  
- **BNBUSDT** - Binance Coin
- **ADAUSDT** - Cardano
- **XRPUSDT** - Ripple
- **DOTUSDT** - Polkadot
- **LINKUSDT** - Chainlink
- **LTCUSDT** - Litecoin
- **BCHUSDT** - Bitcoin Cash
- **EOSUSDT** - EOS

### Strategies Covered
- **RSIStrategy** - Relative Strength Index
- **EnhancedRSIStrategy** - Enhanced RSI with filters
- **RSIDivergenceStrategy** - RSI Divergence detection
- **MovingAverageCrossover** - Moving Average crossovers
- **BollingerBandStrategy** - Bollinger Bands
- **MomentumStrategy** - Momentum indicators
- **TrendFollowingStrategy** - Trend following
- **LiveReactiveRSIStrategy** - Live reactive RSI

### Timeframes Covered
- **15m** - 15 minutes
- **30m** - 30 minutes  
- **1h** - 1 hour
- **2h** - 2 hours
- **4h** - 4 hours
- **1d** - 1 day

**Total: ~480 combinations** (10 symbols × 8 strategies × 6 timeframes)

## Integration with Other Bots

The Monitor Bot works seamlessly with the other bots:

1. **backTestBot.py** - Runs historical backtests
2. **testTradingBot.py** - Runs test trading with streak conditions
3. **prodTradingBot.py** - Runs production trading
4. **run_bot_system.py** - Orchestrates all bots

All bots use the shared `BotCore` and output to BigQuery with appropriate `run_name` values:
- `backTestBot` → `run_name = 'backTestBot'`
- `testTradingBot` → `run_name = 'testBot'`
- `prodTradingBot` → `run_name = 'prodBot'`
- `monitorBot` → `run_name = 'monitorBot'`

## Streak-Based Automation

The Monitor Bot integrates with the streak-based automation system:

- **Monitoring Mode**: Collects daily performance data for streak analysis
- **Trading Mode**: Only executes trades when 5+ day positive streaks are detected
- **BigQuery Integration**: All performance data saved for analysis

## Logging and Output

The bot provides detailed logging:
- Current market conditions
- Signal generation
- Performance summaries
- Streak analysis results
- Trade execution logs

All data is saved to BigQuery for persistent storage and analysis.

## Safety Features

- **Streak Conditions**: Trading only enabled when conditions are met
- **Error Handling**: Graceful handling of API errors and data issues
- **Graceful Shutdown**: Clean shutdown on Ctrl+C
- **Rate Limiting**: Built-in delays to avoid API rate limits

## Next Steps

1. **Start with Comprehensive Monitoring**: `python scripts/monitorBot.py` (monitors all 480+ combinations hourly)
2. **Test Active Trading**: `python scripts/monitorBot.py --mode trading --schedule 15m`
3. **Focus on Specific Timeframes**: `python scripts/monitorBot.py --schedule 1h` (hourly combinations only)
4. **Monitor Performance**: Check BigQuery for performance data and streak analysis across all strategies 