# BigQuery Setup Guide (Free SQL Database in GCP)

## Why BigQuery?
- ✅ **Free tier**: 1TB queries/month + 10GB storage
- ✅ **Standard SQL**: Full SQL support
- ✅ **Already in GCP**: No new setup needed
- ✅ **Perfect for analytics**: Built for data analysis
- ✅ **No monthly costs**: Pay only for overages

## Step 1: Enable BigQuery API

1. Go to [GCP Console](https://console.cloud.google.com)
2. Search for **"BigQuery"** in the search bar
3. Click on **"BigQuery"**
4. If prompted, click **"Enable"** for the BigQuery API

## Step 2: Install Dependencies

```bash
pip install google-cloud-bigquery==3.17.2
```

## Step 3: Set Up Authentication

You already have this! The BigQuery code uses your existing Firebase credentials:
- File: `config/tradingbot-firebase-API-Key.json`
- This same file works for BigQuery

## Step 4: Test the Setup

```bash
python scripts/test_bigquery.py
```

## Step 5: Run Your Backtest

```bash
python scripts/backTestBot.py
```

## What Happens Automatically:

1. **Dataset Creation**: Creates `tradingbot_data` dataset
2. **Table Creation**: Creates `trades`, `daily_summary`, `performance_metrics` tables
3. **Data Upload**: All trades go to BigQuery instead of files
4. **SQL Queries**: Performance analysis uses real SQL

## BigQuery Benefits:

### 🆓 **Free Tier Limits:**
- **1TB queries/month** (plenty for trading data)
- **10GB storage** (enough for years of trades)
- **No credit card required** for free tier

### 📊 **SQL Features:**
```sql
-- Example queries you can now run:
SELECT 
    symbol,
    strategy,
    COUNT(*) as total_trades,
    SUM(profit) as total_profit,
    AVG(profit) as avg_profit
FROM tradingbot_data.trades
WHERE entry_time >= '2024-01-01'
GROUP BY symbol, strategy
ORDER BY total_profit DESC;
```

### 🔄 **Migration:**
- Your existing Firebase credentials work
- No new API keys needed
- Automatic table creation
- Data stays in GCP

## Cost Comparison:

| Service | Monthly Cost | Setup Complexity |
|---------|-------------|------------------|
| **BigQuery** | **$0** (free tier) | **Easy** |
| Cloud SQL | $10-15/month | Complex |
| Firestore | $0-5/month | Medium |
| File System | $0 | Unreliable |

## Next Steps:

1. **Test the connection**: `python scripts/test_bigquery.py`
2. **Run a backtest**: `python scripts/backTestBot.py`
3. **View your data**: Go to BigQuery console to see your tables
4. **Run SQL queries**: Analyze your trading performance

## Troubleshooting:

### If you get permission errors:
1. Go to BigQuery console
2. Make sure your service account has BigQuery permissions
3. The Firebase service account should work automatically

### If tables don't create:
1. Check the logs for specific errors
2. Make sure BigQuery API is enabled
3. Verify your credentials file exists

## View Your Data:

1. Go to [BigQuery Console](https://console.cloud.google.com/bigquery)
2. Look for `tradingbot_data` dataset
3. Click on `trades` table to see your data
4. Use the "Query" tab to run SQL analysis

That's it! BigQuery is much simpler than Cloud SQL and completely free for your use case. 