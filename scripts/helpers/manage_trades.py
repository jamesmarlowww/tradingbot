"""
Script to manage trades in BigQuery
- Clear old trades by bot type or date
- View trade statistics
- Export trades by bot type
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import argparse

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from utils.bigquery_database import BigQueryDatabase

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_old_trades(run_name=None, days_old=None, confirm=False):
    """
    Clear old trades from BigQuery
    
    Args:
        run_name (str): Specific bot type to clear (e.g., 'backTestBot', 'prod', 'liveTradingTest')
        days_old (int): Only clear trades older than this many days
        confirm (bool): Skip confirmation prompt
    """
    try:
        db = BigQueryDatabase()
        
        # Get current stats before clearing
        stats = db.get_database_stats()
        logger.info(f"Current database stats: {stats}")
        
        if run_name:
            # Clear specific bot type
            if not confirm:
                response = input(f"Are you sure you want to clear ALL trades for '{run_name}'? (yes/no): ")
                if response.lower() != 'yes':
                    logger.info("Operation cancelled")
                    return
            
            logger.info(f"Clearing trades for bot type: {run_name}")
            db.clear_trades(run_name=run_name)
            logger.info(f"Successfully cleared trades for '{run_name}'")
            
        elif days_old:
            # Clear trades older than specified days
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            if not confirm:
                response = input(f"Are you sure you want to clear trades older than {days_old} days (before {cutoff_date.strftime('%Y-%m-%d')})? (yes/no): ")
                if response.lower() != 'yes':
                    logger.info("Operation cancelled")
                    return
            
            logger.info(f"Clearing trades older than {days_old} days")
            # Note: BigQuery doesn't have a direct method for this, so we'll use SQL
            query = f"""
                DELETE FROM `{db.project_id}.{db.dataset_id}.{db.trades_table_id}`
                WHERE entry_time < TIMESTAMP('{cutoff_date.isoformat()}')
            """
            query_job = db.client.query(query)
            query_job.result()
            logger.info(f"Successfully cleared trades older than {days_old} days")
            
        else:
            # Clear all trades
            if not confirm:
                response = input("Are you sure you want to clear ALL trades? (yes/no): ")
                if response.lower() != 'yes':
                    logger.info("Operation cancelled")
                    return
            
            logger.info("Clearing all trades")
            db.clear_trades()
            logger.info("Successfully cleared all trades")
        
        # Get updated stats
        new_stats = db.get_database_stats()
        logger.info(f"Updated database stats: {new_stats}")
        
    except Exception as e:
        logger.error(f"Error clearing trades: {str(e)}")
        raise

def view_trade_statistics(run_name=None, days=None):
    """
    View trade statistics
    
    Args:
        run_name (str): Filter by specific bot type
        days (int): Only show trades from last N days
    """
    try:
        db = BigQueryDatabase()
        
        # Build query
        query = f"""
            SELECT 
                run_name,
                COUNT(*) as total_trades,
                SUM(profit) as total_profit,
                COUNT(CASE WHEN profit > 0 THEN 1 END) as winning_trades,
                COUNT(CASE WHEN profit < 0 THEN 1 END) as losing_trades,
                ROUND(COUNT(CASE WHEN profit > 0 THEN 1 END) * 100.0 / COUNT(*), 2) as win_rate,
                ROUND(AVG(profit), 2) as avg_profit_per_trade,
                MIN(entry_time) as first_trade,
                MAX(entry_time) as last_trade
            FROM `{db.project_id}.{db.dataset_id}.{db.trades_table_id}`
            WHERE profit IS NOT NULL
        """
        
        conditions = []
        if run_name:
            conditions.append(f"run_name = '{run_name}'")
        
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            conditions.append(f"entry_time >= TIMESTAMP('{cutoff_date.isoformat()}')")
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        query += " GROUP BY run_name ORDER BY total_profit DESC"
        
        # Execute query
        query_job = db.client.query(query)
        results = query_job.result()
        
        # Convert to list to avoid iterator issues
        results_list = list(results)
        
        # Display results
        print("\n" + "="*80)
        print("TRADE STATISTICS")
        print("="*80)
        
        for row in results_list:
            print(f"\nBot Type: {row.run_name}")
            print(f"  Total Trades: {row.total_trades}")
            print(f"  Total Profit: ${row.total_profit:,.2f}")
            print(f"  Winning Trades: {row.winning_trades}")
            print(f"  Losing Trades: {row.losing_trades}")
            print(f"  Win Rate: {row.win_rate}%")
            print(f"  Avg Profit per Trade: ${row.avg_profit_per_trade:,.2f}")
            print(f"  First Trade: {row.first_trade}")
            print(f"  Last Trade: {row.last_trade}")
        
        if not results_list:
            print("No trades found matching the criteria")
        
        print("="*80)
        
    except Exception as e:
        logger.error(f"Error viewing statistics: {str(e)}")
        raise

def export_trades_by_bot_type(run_name, filename=None):
    """
    Export trades for a specific bot type to CSV
    
    Args:
        run_name (str): Bot type to export
        filename (str): Output filename
    """
    try:
        db = BigQueryDatabase()
        
        if not filename:
            filename = f"trades_{run_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        logger.info(f"Exporting trades for '{run_name}' to {filename}")
        
        # Export trades
        df = db.export_to_csv({'run_name': run_name}, filename)
        
        logger.info(f"Successfully exported {len(df)} trades to {filename}")
        
        # Show summary
        if not df.empty:
            total_profit = df['profit'].sum()
            winning_trades = len(df[df['profit'] > 0])
            win_rate = (winning_trades / len(df)) * 100
            
            print(f"\nExport Summary for '{run_name}':")
            print(f"  Total Trades: {len(df)}")
            print(f"  Total Profit: ${total_profit:,.2f}")
            print(f"  Win Rate: {win_rate:.2f}%")
            print(f"  File: {filename}")
        
    except Exception as e:
        logger.error(f"Error exporting trades: {str(e)}")
        raise

def list_bot_types():
    """List all available bot types in the database"""
    try:
        db = BigQueryDatabase()
        
        query = f"""
            SELECT DISTINCT run_name, COUNT(*) as trade_count
            FROM `{db.project_id}.{db.dataset_id}.{db.trades_table_id}`
            WHERE run_name IS NOT NULL
            GROUP BY run_name
            ORDER BY trade_count DESC
        """
        
        query_job = db.client.query(query)
        results = query_job.result()
        
        # Convert to list to avoid iterator issues
        results_list = list(results)
        
        print("\n" + "="*50)
        print("AVAILABLE BOT TYPES")
        print("="*50)
        
        for row in results_list:
            print(f"{row.run_name}: {row.trade_count} trades")
        
        if not results_list:
            print("No bot types found in database")
        
        print("="*50)
        
    except Exception as e:
        logger.error(f"Error listing bot types: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Manage trades in BigQuery')
    parser.add_argument('action', choices=['clear', 'stats', 'export', 'list'], 
                       help='Action to perform')
    parser.add_argument('--run-name', type=str, 
                       help='Bot type (e.g., backTestBot, prod, liveTradingTest)')
    parser.add_argument('--days', type=int, 
                       help='Number of days (for clear or stats)')
    parser.add_argument('--filename', type=str, 
                       help='Output filename for export')
    parser.add_argument('--confirm', action='store_true', 
                       help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    try:
        if args.action == 'clear':
            clear_old_trades(run_name=args.run_name, days_old=args.days, confirm=args.confirm)
        elif args.action == 'stats':
            view_trade_statistics(run_name=args.run_name, days=args.days)
        elif args.action == 'export':
            if not args.run_name:
                print("Error: --run-name is required for export action")
                return
            export_trades_by_bot_type(args.run_name, args.filename)
        elif args.action == 'list':
            list_bot_types()
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 