# Bot Type Management Guide

## Overview

Your BigQuery setup already includes a `run_name` column that serves as the "bot type" identifier. This allows you to:

- ✅ **Separate different types of trading runs** (backtest, production, live testing)
- ✅ **Clear old trades by bot type**
- ✅ **Analyze performance by bot type**
- ✅ **Export trades by bot type**

## Current Bot Types

The system automatically uses these bot types:

- **`backTestBot`** - Default for backtesting (set in `scripts/backTestBot.py`)
- **`testBot`** - Used in test scripts
- **`prod`** - For production trading
- **`liveTradingTest`** - For live trading tests

## How to Use Different Bot Types

### Method 1: Environment Variable (Recommended)

Set the `RUN_NAME` environment variable before running your bot:

```bash
# For backtesting
export RUN_NAME=backTestBot
python scripts/backTestBot.py

# For production
export RUN_NAME=prod
python scripts/prodTradingBot.py

# For live testing
export RUN_NAME=liveTradingTest
python scripts/testTradingBot.py
```

### Method 2: Use the Bot Runner Script

```bash
python scripts/run_bot_types.py
```

This interactive script lets you choose which bot type to run.

## Managing Old Trades

### View Current Bot Types and Trade Counts

```bash
python scripts/manage_trades.py list
```

### View Trade Statistics

```bash
# All trades
python scripts/manage_trades.py stats

# Specific bot type
python scripts/manage_trades.py stats --run-name backTestBot

# Last 30 days
python scripts/manage_trades.py stats --days 30

# Specific bot type, last 7 days
python scripts/manage_trades.py stats --run-name prod --days 7
```

### Clear Old Trades

```bash
# Clear all trades (with confirmation)
python scripts/manage_trades.py clear

# Clear specific bot type
python scripts/manage_trades.py clear --run-name backTestBot

# Clear trades older than 30 days
python scripts/manage_trades.py clear --days 30

# Skip confirmation prompt
python scripts/manage_trades.py clear --run-name backTestBot --confirm
```

### Export Trades by Bot Type

```bash
# Export backtest trades
python scripts/manage_trades.py export --run-name backTestBot

# Export with custom filename
python scripts/manage_trades.py export --run-name prod --filename prod_trades.csv
```

## BigQuery Schema

Your trades table includes these key columns:

```sql
CREATE TABLE trades (
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    strategy STRING NOT NULL,
    symbol STRING NOT NULL,
    timeframe STRING NOT NULL,
    trade_type STRING NOT NULL,
    entry_price FLOAT64 NOT NULL,
    position_size FLOAT64 NOT NULL,
    stop_loss FLOAT64,
    take_profit FLOAT64,
    profit FLOAT64,
    fees FLOAT64,
    created_at TIMESTAMP,
    run_name STRING  -- This is your "bot type" column
);
```

## Example SQL Queries

### Compare Performance by Bot Type

```sql
SELECT 
    run_name,
    COUNT(*) as total_trades,
    SUM(profit) as total_profit,
    AVG(profit) as avg_profit,
    COUNT(CASE WHEN profit > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate
FROM `your-project.tradingbot_data.trades`
WHERE profit IS NOT NULL
GROUP BY run_name
ORDER BY total_profit DESC;
```

### Get Recent Trades by Bot Type

```sql
SELECT *
FROM `your-project.tradingbot_data.trades`
WHERE run_name = 'prod'
  AND entry_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
ORDER BY entry_time DESC;
```

### Delete Old Trades by Bot Type

```sql
DELETE FROM `your-project.tradingbot_data.trades`
WHERE run_name = 'backTestBot'
  AND entry_time < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY);
```

## Best Practices

1. **Use descriptive bot types**: `backTestBot`, `prod`, `liveTradingTest`, `paperTrading`
2. **Clear old backtest data regularly**: Keep only recent backtest results
3. **Export important data**: Export production trades before clearing
4. **Monitor storage costs**: BigQuery free tier includes 10GB storage
5. **Use consistent naming**: Stick to a naming convention for bot types

## Cost Management

- **BigQuery Free Tier**: 1TB queries/month + 10GB storage
- **Storage Cost**: ~$0.02/GB/month after free tier
- **Query Cost**: ~$5/TB after free tier

For typical trading bot usage, you'll likely stay within the free tier limits.

## Troubleshooting

### If trades aren't being tagged correctly:

1. Check that `RUN_NAME` environment variable is set
2. Verify the bot script is reading the environment variable
3. Check BigQuery logs for any errors

### If you can't clear trades:

1. Ensure you have proper BigQuery permissions
2. Check that the table exists and is accessible
3. Verify the `run_name` value matches exactly (case-sensitive)

### If performance queries are slow:

1. Add filters by date range
2. Use the `run_name` filter to limit data
3. Consider creating summary tables for frequently accessed data 