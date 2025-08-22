# GCP Cloud SQL PostgreSQL Setup Guide

## Prerequisites
1. Google Cloud Platform account
2. Google Cloud CLI (gcloud) installed
3. A GCP project with billing enabled

## Step 1: Enable Required APIs

```bash
# Enable Cloud SQL Admin API
gcloud services enable sqladmin.googleapis.com

# Enable Cloud SQL API
gcloud services enable sql-component.googleapis.com

# Enable Cloud Build API (for connection)
gcloud services enable cloudbuild.googleapis.com
```

## Step 2: Create Cloud SQL Instance

```bash
# Create a PostgreSQL instance
gcloud sql instances create tradingbot-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --storage-type=SSD \
    --storage-size=10GB \
    --backup-start-time=02:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=03:00 \
    --authorized-networks=0.0.0.0/0 \
    --root-password=YOUR_SECURE_PASSWORD \
    --project=YOUR_PROJECT_ID
```

## Step 3: Create Database and User

```bash
# Create the trading database
gcloud sql databases create tradingbot_db \
    --instance=tradingbot-db

# Create a dedicated user for the application
gcloud sql users create tradingbot_user \
    --instance=tradingbot-db \
    --password=YOUR_APP_PASSWORD
```

## Step 4: Get Connection Information

```bash
# Get the connection name
gcloud sql instances describe tradingbot-db \
    --format="value(connectionName)"

# Get the public IP address
gcloud sql instances describe tradingbot-db \
    --format="value(ipAddresses[0].ipAddress)"
```

## Step 5: Test Connection

```bash
# Connect to the database
gcloud sql connect tradingbot-db --user=postgres
```

## Step 6: Create Tables (Run in PostgreSQL)

```sql
-- Connect to the tradingbot_db
\c tradingbot_db;

-- Create trades table
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    strategy VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    trade_type VARCHAR(10) NOT NULL,
    entry_price DECIMAL(20,8) NOT NULL,
    position_size DECIMAL(20,8) NOT NULL,
    stop_loss DECIMAL(20,8),
    take_profit DECIMAL(20,8),
    profit DECIMAL(20,8),
    fees DECIMAL(20,8) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    run_name VARCHAR(50) DEFAULT 'backTestBot'
);

-- Create daily_summary table
CREATE TABLE daily_summary (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    trades_count INTEGER DEFAULT 0,
    total_profit DECIMAL(20,8) DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, symbol, strategy, timeframe)
);

-- Create performance_metrics table
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    total_trades INTEGER DEFAULT 0,
    total_profit DECIMAL(20,8) DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2) DEFAULT 0,
    max_drawdown DECIMAL(10,4) DEFAULT 0,
    sharpe_ratio DECIMAL(10,4) DEFAULT 0,
    avg_profit_per_trade DECIMAL(20,8) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, strategy, timeframe)
);

-- Create indexes for better performance
CREATE INDEX idx_trades_symbol_strategy ON trades(symbol, strategy);
CREATE INDEX idx_trades_entry_time ON trades(entry_time);
CREATE INDEX idx_trades_run_name ON trades(run_name);
CREATE INDEX idx_daily_summary_date ON daily_summary(date);
CREATE INDEX idx_daily_summary_symbol_strategy ON daily_summary(symbol, strategy);
CREATE INDEX idx_performance_metrics_symbol_strategy ON performance_metrics(symbol, strategy);

-- Grant permissions to the application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tradingbot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tradingbot_user;
```

## Step 7: Environment Variables

Add these to your `.env` file or environment:

```bash
# Database Configuration
DB_HOST=YOUR_INSTANCE_IP
DB_PORT=5432
DB_NAME=tradingbot_db
DB_USER=tradingbot_user
DB_PASSWORD=YOUR_APP_PASSWORD
DB_SSL_MODE=require

# Optional: Use Cloud SQL Proxy for local development
# DB_HOST=localhost
# DB_PORT=5432
```

## Step 8: Install Cloud SQL Proxy (Optional for local development)

```bash
# Download Cloud SQL Proxy
curl -o cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64

# Make it executable
chmod +x cloud_sql_proxy

# Start the proxy
./cloud_sql_proxy -instances=YOUR_PROJECT:us-central1:tradingbot-db=tcp:5432
```

## Security Notes

1. **Never commit passwords to version control**
2. **Use environment variables for sensitive data**
3. **Consider using Cloud SQL Proxy for production**
4. **Set up proper firewall rules**
5. **Enable SSL connections**
6. **Regularly rotate passwords**

## Cost Estimation

- **db-f1-micro**: ~$7.50/month
- **Storage**: ~$0.17/GB/month
- **Network**: ~$0.12/GB (outbound)

Total estimated cost: ~$10-15/month for a small trading bot. 