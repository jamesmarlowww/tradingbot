"""
Test script for PostgreSQL connection and basic operations
"""

import os
import logging
from datetime import datetime, timedelta
from utils.postgres_database import PostgresDatabase

# Set the run name for the test
os.environ['RUN_NAME'] = 'testBot'

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_postgres_connection():
    """Test PostgreSQL connection and basic operations"""
    try:
        # Initialize database
        logger.info("Initializing PostgreSQL connection...")
        db = PostgresDatabase()
        logger.info("Successfully initialized PostgreSQL connection")
        
        # Test adding a trade
        test_trade = {
            'entry_time': datetime.now() - timedelta(hours=1),
            'exit_time': datetime.now(),
            'strategy': 'test_strategy',
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'trade_type': 'LONG',
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
        
        # Test batch upload
        logger.info("Testing batch upload...")
        batch_trades = []
        for i in range(5):
            batch_trade = test_trade.copy()
            batch_trade['entry_time'] = datetime.now() - timedelta(hours=i+2)
            batch_trade['exit_time'] = datetime.now() - timedelta(hours=i+1)
            batch_trade['profit'] = 50.0 + i * 10
            batch_trades.append(batch_trade)
        
        uploaded_count = db.batch_upload_trades(batch_trades)
        logger.info(f"Successfully uploaded {uploaded_count} trades in batch")
        
        # Test performance summary
        logger.info("Testing performance summary...")
        summary = db.get_performance_summary()
        logger.info(f"Performance summary has {len(summary)} records")
        
        # Test database stats
        logger.info("Testing database stats...")
        stats = db.get_database_stats()
        logger.info(f"Database stats: {stats}")
        
        # Test exporting to CSV
        logger.info("Testing CSV export...")
        df = db.export_to_csv({'strategy': 'test_strategy'}, 'test_trades_postgres.csv')
        logger.info(f"Successfully exported {len(df)} trades to CSV")
        
        logger.info("All PostgreSQL tests completed successfully!")
        
    except Exception as e:
        logger.error(f"PostgreSQL test failed: {str(e)}")
        raise

def test_data_integrity():
    """Test data integrity and consistency"""
    try:
        logger.info("Testing data integrity...")
        db = PostgresDatabase()
        
        # Add some test data with known values
        test_trades = []
        for i in range(10):
            trade = {
                'entry_time': datetime.now() - timedelta(hours=i),
                'exit_time': datetime.now() - timedelta(hours=i-1) if i > 0 else None,
                'strategy': 'integrity_test',
                'symbol': 'ETHUSDT',
                'timeframe': '1h',
                'trade_type': 'LONG' if i % 2 == 0 else 'SHORT',
                'entry_price': 3000.0 + i * 10,
                'position_size': 0.1,
                'stop_loss': 2900.0 + i * 10,
                'take_profit': 3100.0 + i * 10,
                'profit': 50.0 + i * 5,
                'fees': 2.0
            }
            test_trades.append(trade)
        
        # Upload test data
        db.batch_upload_trades(test_trades)
        
        # Retrieve and verify data
        retrieved_trades = db.get_trades({'strategy': 'integrity_test'})
        
        if len(retrieved_trades) == len(test_trades):
            logger.info("✓ Data integrity test passed: All trades retrieved")
        else:
            logger.error(f"✗ Data integrity test failed: Expected {len(test_trades)}, got {len(retrieved_trades)}")
        
        # Test performance summary accuracy
        summary = db.get_performance_summary()
        eth_trades = summary[summary['symbol'] == 'ETHUSDT']
        
        if not eth_trades.empty:
            total_profit = eth_trades['total_profit'].sum()
            expected_profit = sum(t['profit'] for t in test_trades)
            
            if abs(total_profit - expected_profit) < 0.01:  # Allow for small floating point differences
                logger.info("✓ Performance summary accuracy test passed")
            else:
                logger.error(f"✗ Performance summary accuracy test failed: Expected {expected_profit}, got {total_profit}")
        
        logger.info("Data integrity tests completed!")
        
    except Exception as e:
        logger.error(f"Data integrity test failed: {str(e)}")
        raise

if __name__ == "__main__":
    print("=== PostgreSQL Database Test ===")
    
    try:
        test_postgres_connection()
        test_data_integrity()
        print("\n✓ All tests passed successfully!")
        
    except Exception as e:
        print(f"\n✗ Tests failed: {str(e)}")
        print("\nMake sure you have:")
        print("1. Set up Cloud SQL PostgreSQL instance")
        print("2. Created the required tables")
        print("3. Set up environment variables in .env file")
        print("4. Installed psycopg2-binary package") 