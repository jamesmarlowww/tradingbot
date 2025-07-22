"""
Firestore configuration settings
"""

# Firestore settings
FIRESTORE_PROJECT_ID = "tradingbot-459223"  # Your GCP project ID
FIRESTORE_CREDENTIALS_PATH = "config/tradingbot-firebase-API-Key.json"  # Separate credentials for Firestore

# Collection names
TRADES_COLLECTION = "trades_backTestBot"  # Collection for backtest trades
DAILY_SUMMARY_COLLECTION = "daily_summary"
STRATEGY_PERFORMANCE_COLLECTION = "strategy_performance"
SYMBOL_PERFORMANCE_COLLECTION = "symbol_performance"

# Default settings
DEFAULT_TIMEZONE = "UTC"
DEFAULT_DECIMAL_PLACES = 8  # For price and amount values 