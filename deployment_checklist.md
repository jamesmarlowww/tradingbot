# Digital Ocean Deployment Checklist

## ✅ Repository Files to Verify

### 1. Configuration Files
- [ ] `config/config.py` - Main configuration
- [ ] `config/tradingbot-firebase-API-Key.json` - BigQuery service account credentials
- [ ] `env.example` - Environment variables template
- [ ] `requirements.txt` - Python dependencies

### 2. Core Scripts
- [ ] `scripts/testTradingBot.py` - Main bot script
- [ ] `utils/bot_core.py` - Shared bot logic
- [ ] `utils/bigquery_database.py` - BigQuery integration
- [ ] `trading/strategies.py` - Trading strategies
- [ ] `trading/execution.py` - Trade execution

### 3. Dependencies
- [ ] `requirements.txt` - Check all dependencies are listed
- [ ] Verify no local-only imports or paths

## 🔧 BigQuery Setup for Droplet

### 1. Service Account Credentials
- [ ] `config/tradingbot-firebase-API-Key.json` is in your repo
- [ ] Service account has BigQuery permissions
- [ ] Project ID is correct in the credentials

### 2. Test BigQuery Connection
```bash
# On your local machine, test the connection
python -c "from utils.bigquery_database import BigQueryDatabase; db = BigQueryDatabase(); print('BigQuery connection successful')"
```

## 🌐 API Keys and Environment

### 1. Binance API
- [ ] API keys work with testnet
- [ ] API keys have correct permissions
- [ ] Rate limits are acceptable for 15-minute intervals

### 2. Environment Variables
- [ ] `API_KEY` - Binance API key
- [ ] `API_SECRET` - Binance API secret
- [ ] `TESTNET=true` - Use testnet for safety

## 📁 Directory Structure
```
trading-bot/
├── config/
│   ├── config.py
│   ├── tradingbot-firebase-API-Key.json
│   └── automation_config.py
├── scripts/
│   └── testTradingBot.py
├── utils/
│   ├── bot_core.py
│   └── bigquery_database.py
├── trading/
│   ├── strategies.py
│   └── execution.py
├── requirements.txt
└── env.example
```

## 🚀 Deployment Steps

### 1. Repository Preparation
```bash
# Ensure all files are committed
git add .
git commit -m "Prepare for Digital Ocean deployment"
git push
```

### 2. Droplet Setup
```bash
# Connect to droplet
ssh root@your-droplet-ip

# Clone repository
git clone https://github.com/your-username/trading-bot.git
cd trading-bot

# Set up environment
cp env.example .env
nano .env  # Edit with your API keys
```

### 3. Test BigQuery Connection on Droplet
```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Test BigQuery connection
python -c "from utils.bigquery_database import BigQueryDatabase; db = BigQueryDatabase(); print('BigQuery connection successful')"
```

## ⚠️ Potential Issues

### 1. BigQuery Authentication
- **Issue**: Service account credentials not found
- **Solution**: Ensure `tradingbot-firebase-API-Key.json` is in the repo

### 2. Network Connectivity
- **Issue**: Droplet can't reach Binance API
- **Solution**: Test with `curl https://testnet.binance.vision/api/v3/time`

### 3. Python Dependencies
- **Issue**: Missing packages
- **Solution**: Check `requirements.txt` is complete

### 4. File Permissions
- **Issue**: Can't read config files
- **Solution**: Ensure proper file permissions on droplet

## 🔍 Pre-Deployment Tests

### 1. Local BigQuery Test
```bash
python check_streak_status.py
```

### 2. Bot Startup Test
```bash
python scripts/testTradingBot.py
# Let it run for 1-2 cycles, then Ctrl+C
```

### 3. API Connection Test
```bash
python -c "from binance.client import Client; client = Client('test', 'test'); print(client.get_server_time())"
```

## 📊 Monitoring Setup

### 1. Log Files
- [ ] Bot logs to `data/logs/trading_bot.log`
- [ ] Systemd service logs available

### 2. BigQuery Monitoring
- [ ] Check trades are being uploaded
- [ ] Monitor for upload errors
- [ ] Verify `run_name` is correct

### 3. Performance Monitoring
- [ ] CPU usage
- [ ] Memory usage
- [ ] Disk space
- [ ] Network connectivity 