#!/bin/bash

# Digital Ocean Trading Bot Deployment Script
# Run this on your Digital Ocean droplet

set -e

echo "🚀 Setting up Trading Bot on Digital Ocean..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "📦 Installing required packages..."
sudo apt install -y python3 python3-pip python3-venv git curl wget

# Create trading bot user
echo "👤 Creating trading bot user..."
sudo useradd -m -s /bin/bash tradingbot || echo "User already exists"
sudo usermod -aG sudo tradingbot

# Create log directory
echo "📁 Creating log directory..."
sudo mkdir -p /var/log/tradingbot
sudo chown tradingbot:tradingbot /var/log/tradingbot

# Clone or update repository
echo "📥 Setting up repository..."
if [ ! -d "/home/tradingbot/btc-trading" ]; then
    sudo -u tradingbot git clone https://github.com/yourusername/btc-trading.git /home/tradingbot/btc-trading
else
    sudo -u tradingbot git -C /home/tradingbot/btc-trading pull
fi

# Set up Python environment
echo "🐍 Setting up Python environment..."
sudo -u tradingbot python3 -m venv /home/tradingbot/btc-trading/venv
sudo -u tradingbot /home/tradingbot/btc-trading/venv/bin/pip install --upgrade pip
sudo -u tradingbot /home/tradingbot/btc-trading/venv/bin/pip install -r /home/tradingbot/btc-trading/requirements.txt

# Copy service file
echo "⚙️ Setting up systemd service..."
sudo cp /home/tradingbot/btc-trading/tradingbot-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start service
echo "🚀 Starting trading bot service..."
sudo systemctl enable tradingbot-monitor
sudo systemctl start tradingbot-monitor

# Check status
echo "📊 Service status:"
sudo systemctl status tradingbot-monitor --no-pager

echo "✅ Deployment complete!"
echo ""
echo "📋 Useful commands:"
echo "  Check status: sudo systemctl status tradingbot-monitor"
echo "  View logs: sudo journalctl -u tradingbot-monitor -f"
echo "  Stop service: sudo systemctl stop tradingbot-monitor"
echo "  Restart service: sudo systemctl restart tradingbot-monitor"
echo ""
echo "📁 Log files: /var/log/tradingbot/monitorbot.log"
