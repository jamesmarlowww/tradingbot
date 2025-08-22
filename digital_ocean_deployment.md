# Digital Ocean Deployment Guide

## Prerequisites
- Digital Ocean account
- SSH access to your droplet
- Python 3.8+ installed on droplet

## Step 1: Set Up Droplet
```bash
# Connect to your droplet
ssh root@your-droplet-ip

# Update system
apt update && apt upgrade -y

# Install Python and dependencies
apt install python3 python3-pip python3-venv git -y
```

## Step 2: Clone Repository
```bash
# Clone your trading bot repository
git clone https://github.com/your-username/trading-bot.git
cd trading-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Configure Environment
```bash
# Copy and edit config files
cp env.example .env
nano .env

# Set your API keys and configuration
API_KEY=your_binance_api_key
API_SECRET=your_binance_secret
TESTNET=true
```

## Step 4: Create Systemd Service
```bash
# Create service file
sudo nano /etc/systemd/system/trading-bot.service
```

Add this content:
```ini
[Unit]
Description=Trading Bot Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/trading-bot
Environment=PATH=/root/trading-bot/venv/bin
ExecStart=/root/trading-bot/venv/bin/python scripts/testTradingBot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Step 5: Start the Service
```bash
# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot

# Check status
sudo systemctl status trading-bot

# View logs
sudo journalctl -u trading-bot -f
```

## Step 6: Monitor and Manage
```bash
# Stop the bot
sudo systemctl stop trading-bot

# Restart the bot
sudo systemctl restart trading-bot

# View recent logs
sudo journalctl -u trading-bot --since "1 hour ago"
```

## Step 7: Set Up Log Rotation
```bash
# Create logrotate config
sudo nano /etc/logrotate.d/trading-bot
```

Add:
```
/var/log/trading-bot.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
```

## Monitoring Commands
```bash
# Check if bot is running
sudo systemctl is-active trading-bot

# View real-time logs
sudo journalctl -u trading-bot -f

# Check disk space
df -h

# Check memory usage
free -h
```

## Troubleshooting
- If the bot stops, check logs: `sudo journalctl -u trading-bot -n 50`
- If API errors occur, verify your API keys in `.env`
- If BigQuery errors occur, check your service account credentials 