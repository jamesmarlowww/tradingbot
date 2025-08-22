"""
Test script for Firestore connection and basic operations
"""

import os
import logging
from utils.database import TradingDatabase
from datetime import datetime

# Set the run name for the test
os.environ['RUN_NAME'] = 'testBot'

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_firestore_connection():
    """Test Firestore connection and basic operations"""
    try:
        # Initialize database
        logger.info("Initializing Firestore connection...")
        db = TradingDatabase()
        logger.info("Successfully initialized Firestore connection")
        
        # Test adding a trade
        test_trade = {
            'entry_time': '2024-03-10T10:00:00',
            'exit_time': '2024-03-10T11:00:00',
            'strategy': 'test_strategy',
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'trade_type': 'long',
            'entry_price': 50000.0,
            'position_size': 0.1,
            'stop_loss': 49000.0,
            'take_profit': 52000.0,
            'profit': 100.0,
            'fees': 5.0
        }
        
        logger.info("Adding test trade...")
        trade_id = db.add_trade(test_trade)
        logger.info(f"Successfully added test trade with ID: {trade_id}")
        
        # Test retrieving trades
        logger.info("Retrieving trades...")
        trades = db.get_trades({'strategy': 'test_strategy'})
        logger.info(f"Retrieved {len(trades)} trades")
        
        # Test exporting trades to CSV
        logger.info("Exporting trades to CSV...")
        df = db.export_to_csv({'strategy': 'test_strategy'}, 'test_trades.csv')
        logger.info(f"Successfully exported {len(df)} trades to CSV")
        
        logger.info("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    test_firestore_connection() 