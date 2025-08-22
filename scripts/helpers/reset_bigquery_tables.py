"""
Reset BigQuery tables with correct schema
"""

import sys
import os

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from google.cloud import bigquery
from google.oauth2 import service_account
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_bigquery_tables():
    """Delete and recreate BigQuery tables with correct schema"""
    try:
        # Initialize BigQuery client
        credentials_path = "config/tradingbot-firebase-API-Key.json"
        if os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/bigquery"]
            )
            client = bigquery.Client(credentials=credentials)
        else:
            client = bigquery.Client()
        
        project_id = client.project
        dataset_id = "tradingbot_data"
        
        logger.info(f"Connected to BigQuery project: {project_id}")
        
        # Delete existing tables
        tables_to_delete = ["trades", "daily_summary", "performance_metrics"]
        for table_name in tables_to_delete:
            table_ref = client.dataset(dataset_id).table(table_name)
            try:
                client.delete_table(table_ref, not_found_ok=True)
                logger.info(f"Deleted table: {table_name}")
            except Exception as e:
                logger.warning(f"Could not delete table {table_name}: {str(e)}")
        
        # Recreate tables with correct schema
        dataset_ref = client.dataset(dataset_id)
        
        # Create trades table
        trades_schema = [
            bigquery.SchemaField("entry_time", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("exit_time", "TIMESTAMP"),
            bigquery.SchemaField("strategy", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("symbol", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("timeframe", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("trade_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("entry_price", "FLOAT64", mode="REQUIRED"),
            bigquery.SchemaField("position_size", "FLOAT64", mode="REQUIRED"),
            bigquery.SchemaField("stop_loss", "FLOAT64"),
            bigquery.SchemaField("take_profit", "FLOAT64"),
            bigquery.SchemaField("profit", "FLOAT64"),
            bigquery.SchemaField("fees", "FLOAT64"),
            bigquery.SchemaField("created_at", "TIMESTAMP"),
            bigquery.SchemaField("run_name", "STRING")
        ]
        
        trades_table_ref = dataset_ref.table("trades")
        trades_table = bigquery.Table(trades_table_ref, schema=trades_schema)
        trades_table = client.create_table(trades_table)
        logger.info("Created table: trades")
        
        # Create daily_summary table
        daily_summary_schema = [
            bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("symbol", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("strategy", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("timeframe", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("trades_count", "INTEGER"),
            bigquery.SchemaField("total_profit", "FLOAT64"),
            bigquery.SchemaField("winning_trades", "INTEGER"),
            bigquery.SchemaField("losing_trades", "INTEGER"),
            bigquery.SchemaField("win_rate", "FLOAT64"),
            bigquery.SchemaField("created_at", "TIMESTAMP")
        ]
        
        daily_summary_table_ref = dataset_ref.table("daily_summary")
        daily_summary_table = bigquery.Table(daily_summary_table_ref, schema=daily_summary_schema)
        daily_summary_table = client.create_table(daily_summary_table)
        logger.info("Created table: daily_summary")
        
        # Create performance_metrics table
        performance_metrics_schema = [
            bigquery.SchemaField("symbol", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("strategy", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("timeframe", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("total_trades", "INTEGER"),
            bigquery.SchemaField("total_profit", "FLOAT64"),
            bigquery.SchemaField("winning_trades", "INTEGER"),
            bigquery.SchemaField("win_rate", "FLOAT64"),
            bigquery.SchemaField("max_drawdown", "FLOAT64"),
            bigquery.SchemaField("sharpe_ratio", "FLOAT64"),
            bigquery.SchemaField("avg_profit_per_trade", "FLOAT64"),
            bigquery.SchemaField("created_at", "TIMESTAMP"),
            bigquery.SchemaField("updated_at", "TIMESTAMP")
        ]
        
        performance_metrics_table_ref = dataset_ref.table("performance_metrics")
        performance_metrics_table = bigquery.Table(performance_metrics_table_ref, schema=performance_metrics_schema)
        performance_metrics_table = client.create_table(performance_metrics_table)
        logger.info("Created table: performance_metrics")
        
        logger.info("Successfully reset all BigQuery tables!")
        
    except Exception as e:
        logger.error(f"Error resetting BigQuery tables: {str(e)}")
        raise

if __name__ == "__main__":
    print("=== Resetting BigQuery Tables ===")
    try:
        reset_bigquery_tables()
        print("✓ Tables reset successfully!")
        print("\nYou can now run: python scripts/test_bigquery.py")
    except Exception as e:
        print(f"✗ Failed to reset tables: {str(e)}") 