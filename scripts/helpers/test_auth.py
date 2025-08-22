#!/usr/bin/env python3
"""
Test BigQuery authentication and permissions
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import bigquery
from google.oauth2 import service_account
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_auth():
    """Test BigQuery authentication"""
    try:
        # Check if service account file exists
        credentials_path = "config/tradingbot-firebase-API-Key.json"
        if os.path.exists(credentials_path):
            logger.info(f"Found service account file: {credentials_path}")
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/bigquery"]
            )
            client = bigquery.Client(credentials=credentials, project="tradingbot-459223")
            logger.info("Using service account authentication")
        else:
            logger.info("No service account file found, using default credentials")
            client = bigquery.Client(project="tradingbot-459223")
        
        # Test basic connection
        logger.info(f"Connected to project: {client.project}")
        
        # Test if we can query the dataset
        try:
            query = """
            SELECT COUNT(*) as count 
            FROM `tradingbot-459223.tradingbot_data.trades` 
            LIMIT 1
            """
            query_job = client.query(query)
            results = query_job.result()
            for row in results:
                logger.info(f"Successfully queried trades table. Row count: {row.count}")
            logger.info("✅ Authentication successful - can read from BigQuery")
            
        except Exception as e:
            logger.error(f"❌ Cannot query trades table: {str(e)}")
            
        # Test if we can write to the dataset
        try:
            # Try to insert a test row
            query = """
            INSERT INTO `tradingbot-459223.tradingbot_data.trades` 
            (entry_time, strategy, symbol, timeframe, trade_type, entry_price, position_size, run_name)
            VALUES (CURRENT_TIMESTAMP(), 'test', 'BTCUSDT', '1h', 'BUY', 50000.0, 0.001, 'auth_test')
            """
            query_job = client.query(query)
            query_job.result()
            logger.info("✅ Authentication successful - can write to BigQuery")
            
            # Clean up test data
            cleanup_query = """
            DELETE FROM `tradingbot-459223.tradingbot_data.trades` 
            WHERE run_name = 'auth_test'
            """
            cleanup_job = client.query(cleanup_query)
            cleanup_job.result()
            logger.info("✅ Cleaned up test data")
            
        except Exception as e:
            logger.error(f"❌ Cannot write to trades table: {str(e)}")
            
    except Exception as e:
        logger.error(f"❌ Authentication failed: {str(e)}")

if __name__ == "__main__":
    test_auth() 