"""
Test script to add sample trades to BigQuery with different bot types
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import random

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from utils.bigquery_database import BigQueryDatabase

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_trades():
    """Create sample trades for testing bot types"""
    
    # Set different bot types
    bot_types = ['backTestBot', 'prod', 'liveTradingTest', 'paperTrading']
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT']
    strategies = ['RSIStrategy', 'EnhancedRSIStrategy', 'BollingerBandStrategy', 'MovingAverageCrossover']
    timeframes = ['15m', '30m', '1h', '4h']
    
    test_trades = []
    
    # Create trades for each bot type
    for bot_type in bot_types:
        # Set environment variable for this bot type
        os.environ['RUN_NAME'] = bot_type
        
        # Create 10-20 trades for each bot type
        num_trades = random.randint(10, 20)
        
        for i in range(num_trades):
            # Random trade data
            symbol = random.choice(symbols)
            strategy = random.choice(strategies)
            timeframe = random.choice(timeframes)
            
            # Random dates within last 30 days
            entry_time = datetime.now() - timedelta(days=random.randint(1, 30), hours=random.randint(0, 23))
            exit_time = entry_time + timedelta(hours=random.randint(1, 48))
            
            # Random prices and profits
            entry_price = random.uniform(20000, 70000) if symbol == 'BTCUSDT' else random.uniform(1000, 5000)
            exit_price = entry_price * random.uniform(0.95, 1.05)  # ±5% change
            position_size = random.uniform(0.01, 0.1)
            profit = (exit_price - entry_price) * position_size
            fees = abs(profit) * 0.001  # 0.1% fee
            
            trade = {
                'entry_time': entry_time,
                'exit_time': exit_time,
                'strategy': strategy,
                'symbol': symbol,
                'timeframe': timeframe,
                'trade_type': 'LONG' if profit > 0 else 'SHORT',
                'entry_price': entry_price,
                'position_size': position_size,
                'stop_loss': entry_price * 0.98,
                'take_profit': entry_price * 1.03,
                'profit': profit - fees,
                'fees': fees
            }
            
            test_trades.append(trade)
    
    return test_trades

def main():
    """Main function to test BigQuery with different bot types"""
    
    logger.info("Creating test trades for different bot types...")
    
    # Create test trades
    test_trades = create_test_trades()
    
    logger.info(f"Created {len(test_trades)} test trades")
    
    # Initialize BigQuery database
    db = BigQueryDatabase()
    
    # Clear existing trades first
    logger.info("Clearing existing trades...")
    db.clear_trades()
    
    # Upload test trades
    logger.info("Uploading test trades to BigQuery...")
    uploaded_count = db.batch_upload_trades(test_trades, batch_size=100)
    
    logger.info(f"Successfully uploaded {uploaded_count} trades to BigQuery")
    
    # Test the management script
    logger.info("\n" + "="*60)
    logger.info("TESTING BOT TYPE MANAGEMENT")
    logger.info("="*60)
    
    # List bot types
    logger.info("\n1. Listing available bot types:")
    os.system("python scripts/manage_trades.py list")
    
    # Show statistics
    logger.info("\n2. Showing trade statistics:")
    os.system("python scripts/manage_trades.py stats")
    
    # Show statistics for specific bot type
    logger.info("\n3. Showing statistics for backTestBot:")
    os.system("python scripts/manage_trades.py stats --run-name backTestBot")
    
    # Export trades for specific bot type
    logger.info("\n4. Exporting backTestBot trades:")
    os.system("python scripts/manage_trades.py export --run-name backTestBot --filename test_backTestBot_trades.csv")
    
    logger.info("\n" + "="*60)
    logger.info("TEST COMPLETED")
    logger.info("="*60)
    logger.info("You can now test clearing trades by bot type:")
    logger.info("python scripts/manage_trades.py clear --run-name backTestBot")
    logger.info("python scripts/manage_trades.py clear --days 7")

if __name__ == "__main__":
    main() 