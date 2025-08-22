"""
Migration script to move data from file-based system to PostgreSQL
"""

import os
import sys
import pandas as pd
import logging
from datetime import datetime
from typing import List, Dict, Any

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from utils.postgres_database import PostgresDatabase

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_csv_trades_to_postgres():
    """Migrate trades from CSV files to PostgreSQL"""
    try:
        # Initialize PostgreSQL database
        db = PostgresDatabase()
        logger.info("Connected to PostgreSQL database")
        
        # Check for existing CSV files
        csv_files = [
            'output/all_trades.csv',
            'output/summary_report_aggregated.csv'
        ]
        
        migrated_count = 0
        
        for csv_file in csv_files:
            if os.path.exists(csv_file):
                logger.info(f"Migrating data from {csv_file}")
                
                # Read CSV file
                df = pd.read_csv(csv_file)
                logger.info(f"Found {len(df)} records in {csv_file}")
                
                # Convert DataFrame to list of dictionaries
                trades_data = []
                
                for _, row in df.iterrows():
                    # Handle different CSV formats
                    if 'entry_time' in row and 'exit_time' in row:
                        # This is a trades CSV
                        trade = {
                            'entry_time': pd.to_datetime(row['entry_time']),
                            'exit_time': pd.to_datetime(row['exit_time']) if pd.notna(row['exit_time']) else None,
                            'strategy': row['strategy'],
                            'symbol': row['symbol'],
                            'timeframe': row['timeframe'],
                            'trade_type': row['trade_type'],
                            'entry_price': float(row['entry_price']),
                            'position_size': float(row['position_size']),
                            'stop_loss': float(row['stop_loss']) if pd.notna(row['stop_loss']) else None,
                            'take_profit': float(row['take_profit']) if pd.notna(row['take_profit']) else None,
                            'profit': float(row['profit']) if pd.notna(row['profit']) else 0,
                            'fees': float(row['fees']) if pd.notna(row['fees']) else 0
                        }
                        trades_data.append(trade)
                    
                    elif 'date' in row and 'pair' in row and 'strategy' in row:
                        # This is a summary CSV - convert to daily summary format
                        daily_summary = {
                            'date': pd.to_datetime(row['date']).date(),
                            'symbol': row['pair'],
                            'strategy': row['strategy'],
                            'timeframe': row.get('period', row.get('timeframe', '1h')),
                            'trades_count': int(row.get('total_trades', row.get('trades', 0))),
                            'total_profit': float(row.get('total_profit', row.get('profit', 0))),
                            'winning_trades': int(row.get('winning_trades', 0)),
                            'losing_trades': int(row.get('total_trades', 0)) - int(row.get('winning_trades', 0)),
                            'win_rate': float(row.get('win_rate', 0))
                        }
                        
                        # Save daily summary
                        try:
                            db.save_daily_summary([daily_summary])
                            migrated_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to save daily summary: {str(e)}")
                
                # Upload trades data if any
                if trades_data:
                    uploaded_count = db.batch_upload_trades(trades_data)
                    migrated_count += uploaded_count
                    logger.info(f"Migrated {uploaded_count} trades from {csv_file}")
        
        logger.info(f"Migration completed. Total records migrated: {migrated_count}")
        return migrated_count
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

def verify_migration():
    """Verify that migration was successful"""
    try:
        db = PostgresDatabase()
        
        # Get database stats
        stats = db.get_database_stats()
        logger.info("Database stats after migration:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        # Get performance summary
        summary = db.get_performance_summary()
        logger.info(f"Performance summary has {len(summary)} records")
        
        if len(summary) > 0:
            logger.info("Sample performance data:")
            logger.info(summary.head().to_string())
        
        logger.info("Migration verification completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration verification failed: {str(e)}")
        raise

def cleanup_old_files():
    """Clean up old CSV files after successful migration"""
    try:
        files_to_cleanup = [
            'output/all_trades.csv',
            'output/summary_report_aggregated.csv',
            'output/summary_report_daily.csv',
            'output/summary_report_overall.csv'
        ]
        
        cleaned_count = 0
        for file_path in files_to_cleanup:
            if os.path.exists(file_path):
                # Create backup first
                backup_path = f"{file_path}.backup"
                os.rename(file_path, backup_path)
                logger.info(f"Backed up {file_path} to {backup_path}")
                cleaned_count += 1
        
        logger.info(f"Cleanup completed. {cleaned_count} files backed up.")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise

def main():
    """Main migration function"""
    print("=== Data Migration to PostgreSQL ===")
    
    try:
        # Step 1: Migrate data
        print("\n1. Migrating data from CSV files to PostgreSQL...")
        migrated_count = migrate_csv_trades_to_postgres()
        
        if migrated_count > 0:
            print(f"✓ Successfully migrated {migrated_count} records")
            
            # Step 2: Verify migration
            print("\n2. Verifying migration...")
            verify_migration()
            print("✓ Migration verification passed")
            
            # Step 3: Clean up old files (optional)
            response = input("\n3. Do you want to backup and remove old CSV files? (y/n): ")
            if response.lower() == 'y':
                cleanup_old_files()
                print("✓ Old files backed up and removed")
            else:
                print("✓ Old files preserved")
        
        else:
            print("⚠ No data found to migrate")
        
        print("\n=== Migration Complete ===")
        print("Your trading bot is now using PostgreSQL for data storage!")
        print("\nNext steps:")
        print("1. Test the new system: python scripts/test_postgres.py")
        print("2. Run a backtest: python scripts/backTestBot.py")
        print("3. Monitor the database for any issues")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL is set up and running")
        print("2. Check your .env file configuration")
        print("3. Verify database tables exist")
        print("4. Check network connectivity")

if __name__ == "__main__":
    main() 