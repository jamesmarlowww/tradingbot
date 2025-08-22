"""
PostgreSQL database configuration for trading bot
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database Configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'tradingbot_db')
DB_USER = os.getenv('DB_USER', 'tradingbot_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_SSL_MODE = os.getenv('DB_SSL_MODE', 'require')

# Connection string
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={DB_SSL_MODE}"

# Table names
TRADES_TABLE = "trades"
DAILY_SUMMARY_TABLE = "daily_summary"
PERFORMANCE_METRICS_TABLE = "performance_metrics"

# Default settings
DEFAULT_TIMEZONE = "UTC"
DEFAULT_DECIMAL_PLACES = 8

# Batch settings
BATCH_SIZE = 500
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Logging
LOG_QUERIES = os.getenv('LOG_QUERIES', 'false').lower() == 'true'
LOG_DATA = os.getenv('LOG_DATA', 'false').lower() == 'true' 