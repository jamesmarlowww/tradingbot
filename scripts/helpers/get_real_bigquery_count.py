#!/usr/bin/env python3
"""
Get the real count of trades in BigQuery
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_database import BigQueryDatabase

def get_real_count():
    """Get the actual total count of trades in BigQuery"""
    try:
        db = BigQueryDatabase()
        
        # Use a direct SQL query to get the count
        query = """
        SELECT COUNT(*) as total_trades
        FROM `tradingbot-459223.tradingbot_data.trades`
        """
        
        query_job = db.client.query(query)
        results = query_job.result()
        
        for row in results:
            total_trades = row.total_trades
            print(f"Total trades in BigQuery: {total_trades:,}")
            
            # Also get count by run_name
            query_by_run = """
            SELECT run_name, COUNT(*) as count
            FROM `tradingbot-459223.tradingbot_data.trades`
            GROUP BY run_name
            ORDER BY count DESC
            """
            
            query_job_by_run = db.client.query(query_by_run)
            results_by_run = query_job_by_run.result()
            
            print("\nTrades by run_name:")
            for row in results_by_run:
                print(f"  {row.run_name}: {row.count:,}")
                
    except Exception as e:
        print(f"Error getting count: {e}")

if __name__ == "__main__":
    get_real_count() 