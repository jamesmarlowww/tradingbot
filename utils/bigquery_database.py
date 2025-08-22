"""
BigQuery database operations for trading data
"""

import os
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import time

from google.cloud import bigquery
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

# Determine the run name (e.g., 'backTestBot', 'testBot', 'prodBot')
RUN_NAME = os.getenv('RUN_NAME', 'backTestBot')

class BigQueryDatabase:
    def __init__(self):
        """Initialize BigQuery client"""
        try:
            # Try to use service account credentials if available
            credentials_path = "config/tradingbot-firebase-API-Key.json"
            if os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=["https://www.googleapis.com/auth/bigquery"]
                )
                self.client = bigquery.Client(credentials=credentials, project="tradingbot-459223")
            else:
                # Use default credentials (if running on GCP or with gcloud auth)
                self.client = bigquery.Client(project="tradingbot-459223")
            
            # Set dataset and table names
            self.project_id = self.client.project
            self.dataset_id = "tradingbot_data"
            self.trades_table_id = "trades"
            self.daily_summary_table_id = "daily_summary"
            self.performance_metrics_table_id = "performance_metrics"
            
            # Skip dataset creation/checking - assume it exists
            logger.info(f"Connected to BigQuery project: {self.project_id}")
            logger.info(f"Using existing dataset: {self.dataset_id}")
            
        except Exception as e:
            logger.error(f"Error connecting to BigQuery: {str(e)}")
            raise

    def _setup_dataset_and_tables(self):
        """Create dataset and tables if they don't exist"""
        try:
            # Create dataset
            dataset_ref = self.client.dataset(self.dataset_id)
            try:
                self.client.get_dataset(dataset_ref)
                logger.info(f"Dataset {self.dataset_id} already exists")
            except Exception as e:
                # Check if it's a "not found" error or "already exists" error
                if "Not Found" in str(e) or "404" in str(e):
                    # Dataset doesn't exist, create it
                    dataset = bigquery.Dataset(dataset_ref)
                    dataset.location = "US"
                    dataset = self.client.create_dataset(dataset, timeout=30)
                    logger.info(f"Created dataset {self.dataset_id}")
                elif "Already Exists" in str(e) or "409" in str(e):
                    # Dataset already exists, that's fine
                    logger.info(f"Dataset {self.dataset_id} already exists (caught conflict)")
                else:
                    # Some other error, re-raise it
                    raise e

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

            trades_table_ref = dataset_ref.table(self.trades_table_id)
            try:
                self.client.get_table(trades_table_ref)
                logger.info(f"Table {self.trades_table_id} already exists")
            except Exception:
                table = bigquery.Table(trades_table_ref, schema=trades_schema)
                table = self.client.create_table(table)
                logger.info(f"Created table {self.trades_table_id}")

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

            daily_summary_table_ref = dataset_ref.table(self.daily_summary_table_id)
            try:
                self.client.get_table(daily_summary_table_ref)
                logger.info(f"Table {self.daily_summary_table_id} already exists")
            except Exception:
                table = bigquery.Table(daily_summary_table_ref, schema=daily_summary_schema)
                table = self.client.create_table(table)
                logger.info(f"Created table {self.daily_summary_table_id}")

        except Exception as e:
            logger.error(f"Error setting up dataset and tables: {str(e)}")
            raise

    def _prepare_trade_data(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare trade data for BigQuery insertion"""
        # Ensure timestamps are in correct format
        entry_time = trade_data.get('entry_time')
        exit_time = trade_data.get('exit_time')
        
        if isinstance(entry_time, str):
            entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
        if isinstance(exit_time, str):
            exit_time = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
        
        # Prepare the trade data
        prepared_data = {
            'entry_time': entry_time,
            'exit_time': exit_time,
            'strategy': trade_data['strategy'],
            'symbol': trade_data['symbol'],
            'timeframe': trade_data['timeframe'],
            'trade_type': trade_data['trade_type'],
            'entry_price': trade_data['entry_price'],
            'position_size': trade_data['position_size'],
            'stop_loss': trade_data.get('stop_loss'),
            'take_profit': trade_data.get('take_profit'),
            'profit': trade_data.get('profit', 0),
            'fees': trade_data.get('fees', 0),
            'created_at': datetime.now(),
            'run_name': trade_data.get('run_name', RUN_NAME)  # Use provided run_name or fall back to global
        }
        
        return prepared_data

    def batch_upload_trades(self, trades_data: List[Dict[str, Any]], batch_size: int = 1000) -> int:
        """
        Upload multiple trades in batches to BigQuery.
        
        Args:
            trades_data (list): List of trade dictionaries to upload
            batch_size (int): Number of trades to upload in each batch
            
        Returns:
            int: Number of trades successfully uploaded
        """
        if not trades_data:
            logger.info("No trades to upload")
            return 0

        total_trades = len(trades_data)
        uploaded_count = 0
        
        logger.info(f"Starting batch upload of {total_trades} trades to BigQuery")
        
        # Process trades in batches
        for i in range(0, total_trades, batch_size):
            batch = trades_data[i:i + batch_size]
            current_batch = i // batch_size + 1
            total_batches = (total_trades + batch_size - 1) // batch_size
            
            try:
                # Prepare batch data
                batch_data = []
                for trade in batch:
                    prepared_trade = self._prepare_trade_data(trade)
                    batch_data.append(prepared_trade)
                
                # Convert to DataFrame
                df = pd.DataFrame(batch_data)
                
                # Upload to BigQuery
                table_ref = self.client.dataset(self.dataset_id).table(self.trades_table_id)
                job_config = bigquery.LoadJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                )
                
                job = self.client.load_table_from_dataframe(
                    df, table_ref, job_config=job_config
                )
                job.result()  # Wait for the job to complete
                
                uploaded_count += len(batch)
                logger.info(f"Successfully uploaded batch {current_batch}/{total_batches} ({len(batch)} trades)")
                
            except Exception as batch_error:
                logger.error(f"Error uploading batch {current_batch}: {str(batch_error)}")
                # Continue with next batch even if this one fails
                continue
        
        logger.info(f"Completed batch upload: {uploaded_count}/{total_trades} trades uploaded")
        return uploaded_count

    def add_trade(self, trade_data: Dict[str, Any]) -> int:
        """
        Add a single trade record to BigQuery.
        
        Args:
            trade_data (dict): Trade information
            
        Returns:
            int: ID of the inserted trade (auto-generated)
        """
        try:
            prepared_trade = self._prepare_trade_data(trade_data)
            
            # Convert to DataFrame
            df = pd.DataFrame([prepared_trade])
            
            # Upload to BigQuery
            table_ref = self.client.dataset(self.dataset_id).table(self.trades_table_id)
            job_config = bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            )
            
            job = self.client.load_table_from_dataframe(
                df, table_ref, job_config=job_config
            )
            job.result()  # Wait for the job to complete
            
            logger.info(f"Successfully added trade for {trade_data['symbol']}")
            return 1  # BigQuery doesn't return auto-generated IDs like PostgreSQL
            
        except Exception as e:
            logger.error(f"Error adding trade: {str(e)}")
            raise

    def get_trades(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = 1000) -> List[Dict[str, Any]]:
        """
        Retrieve trades from BigQuery.
        
        Args:
            filters (dict, optional): Filters to apply
            limit (int, optional): Maximum number of trades to return. None for no limit
            
        Returns:
            list: List of trade dictionaries
        """
        try:
            query = f"""
                SELECT * FROM `{self.project_id}.{self.dataset_id}.{self.trades_table_id}`
            """
            
            if filters:
                conditions = []
                for field, value in filters.items():
                    if isinstance(value, str):
                        conditions.append(f"{field} = '{value}'")
                    else:
                        conditions.append(f"{field} = {value}")
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY entry_time DESC"
            if limit is not None:
                query += f" LIMIT {limit}"
            
            # Execute query
            query_job = self.client.query(query)
            results = query_job.result()
            
            # Convert to list of dictionaries
            trades = []
            for row in results:
                trades.append(dict(row.items()))
            
            logger.info(f"Retrieved {len(trades)} trades from BigQuery")
            return trades
            
        except Exception as e:
            logger.error(f"Error retrieving trades: {str(e)}")
            raise

    def clear_trades(self, run_name: Optional[str] = None) -> int:
        """
        Clear trades from BigQuery.
        
        Args:
            run_name (str, optional): Only clear trades from specific run
            
        Returns:
            int: Number of trades deleted
        """
        try:
            if run_name:
                query = f"""
                    DELETE FROM `{self.project_id}.{self.dataset_id}.{self.trades_table_id}`
                    WHERE run_name = '{run_name}'
                """
            else:
                query = f"""
                    DELETE FROM `{self.project_id}.{self.dataset_id}.{self.trades_table_id}`
                    WHERE 1=1
                """
            
            query_job = self.client.query(query)
            query_job.result()
            
            logger.info(f"Cleared trades from BigQuery")
            return 1  # BigQuery doesn't return exact count for DELETE operations
            
        except Exception as e:
            logger.error(f"Error clearing trades: {str(e)}")
            raise

    def export_to_csv(self, filters: Optional[Dict[str, Any]] = None, filename: Optional[str] = None) -> pd.DataFrame:
        """
        Export trades to CSV.
        
        Args:
            filters (dict, optional): Filters to apply
            filename (str, optional): Output filename
            
        Returns:
            pd.DataFrame: DataFrame containing the trades
        """
        try:
            trades = self.get_trades(filters)
            df = pd.DataFrame(trades)
            
            if filename:
                df.to_csv(filename, index=False)
                logger.info(f"Exported {len(df)} trades to {filename}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            raise

    def get_performance_summary(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Get performance summary from trades using BigQuery SQL.
        
        Args:
            start_date (datetime, optional): Start date filter
            end_date (datetime, optional): End date filter
            
        Returns:
            pd.DataFrame: Performance summary DataFrame
        """
        try:
            query = f"""
                SELECT 
                    symbol,
                    strategy,
                    timeframe,
                    COUNT(*) as total_trades,
                    SUM(profit) as total_profit,
                    COUNT(CASE WHEN profit > 0 THEN 1 END) as winning_trades,
                    ROUND(
                        COUNT(CASE WHEN profit > 0 THEN 1 END) * 100.0 / COUNT(*), 2
                    ) as win_rate,
                    ROUND(AVG(profit), 2) as avg_profit_per_trade
                FROM `{self.project_id}.{self.dataset_id}.{self.trades_table_id}`
                WHERE profit IS NOT NULL
            """
            
            if start_date:
                query += f" AND entry_time >= TIMESTAMP('{start_date.isoformat()}')"
            if end_date:
                query += f" AND entry_time <= TIMESTAMP('{end_date.isoformat()}')"
            
            query += " GROUP BY symbol, strategy, timeframe ORDER BY total_profit DESC"
            
            # Execute query
            query_job = self.client.query(query)
            results = query_job.result()
            
            # Convert to DataFrame
            df = pd.DataFrame([dict(row.items()) for row in results])
            
            logger.info(f"Generated performance summary with {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Error generating performance summary: {str(e)}")
            raise

    def save_daily_summary(self, daily_summary: List[Dict[str, Any]]) -> int:
        """
        Save daily summary data to BigQuery.
        
        Args:
            daily_summary (list): List of daily summary dictionaries
            
        Returns:
            int: Number of records saved
        """
        if not daily_summary:
            return 0
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(daily_summary)
            
            # Upload to BigQuery
            table_ref = self.client.dataset(self.dataset_id).table(self.daily_summary_table_id)
            job_config = bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            )
            
            job = self.client.load_table_from_dataframe(
                df, table_ref, job_config=job_config
            )
            job.result()  # Wait for the job to complete
            
            logger.info(f"Saved {len(daily_summary)} daily summary records to BigQuery")
            return len(daily_summary)
            
        except Exception as e:
            logger.error(f"Error saving daily summary: {str(e)}")
            raise

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            dict: Database statistics
        """
        try:
            stats = {}
            
            # Get table counts
            tables = [self.trades_table_id, self.daily_summary_table_id, self.performance_metrics_table_id]
            for table in tables:
                query = f"""
                    SELECT COUNT(*) as count 
                    FROM `{self.project_id}.{self.dataset_id}.{table}`
                """
                query_job = self.client.query(query)
                results = query_job.result()
                for row in results:
                    stats[f"{table}_count"] = row.count
            
            # Get latest trade date
            query = f"""
                SELECT MAX(entry_time) as latest_trade_date
                FROM `{self.project_id}.{self.dataset_id}.{self.trades_table_id}`
            """
            query_job = self.client.query(query)
            results = query_job.result()
            for row in results:
                stats['latest_trade_date'] = row.latest_trade_date
            
            # Get total profit
            query = f"""
                SELECT SUM(profit) as total_profit
                FROM `{self.project_id}.{self.dataset_id}.{self.trades_table_id}`
                WHERE profit IS NOT NULL
            """
            query_job = self.client.query(query)
            results = query_job.result()
            for row in results:
                stats['total_profit'] = row.total_profit or 0
            
            logger.info(f"BigQuery stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            raise
    
    def get_daily_profits(self, start_date, end_date, run_name: str = 'monitorBot') -> List[Dict[str, Any]]:
        """Get daily profit/loss data for a specific run"""
        try:
            # Convert dates to strings for BigQuery
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # Query to get daily aggregated profits
            query = f"""
            SELECT 
                DATE(entry_time) as trade_date,
                SUM(profit) as daily_profit,
                COUNT(*) as trade_count
            FROM `{self.project_id}.{self.dataset_id}.{self.trades_table_id}`
            WHERE run_name = '{run_name}'
            AND DATE(entry_time) BETWEEN '{start_date_str}' AND '{end_date_str}'
            GROUP BY DATE(entry_time)
            ORDER BY trade_date DESC
            """
            
            logger.info(f"Querying daily profits for {run_name} from {start_date_str} to {end_date_str}")
            
            # Execute query
            query_job = self.client.query(query)
            results = query_job.result()
            
            # Convert to list of dictionaries
            daily_profits = []
            for row in results:
                daily_profits.append({
                    'trade_date': row.trade_date,
                    'daily_profit': float(row.daily_profit) if row.daily_profit else 0.0,
                    'trade_count': int(row.trade_count) if row.trade_count else 0
                })
            
            logger.info(f"Found {len(daily_profits)} days of profit data")
            return daily_profits
            
        except Exception as e:
            logger.error(f"Error getting daily profits: {e}")
            return []
    
    def get_profitable_combinations(self, run_name: str = 'monitorBot', streak_days: int = 5) -> List[Dict[str, Any]]:
        """Get combinations that have N consecutive profitable days"""
        try:
            # Query to get combinations with profit streaks
            query = f"""
            WITH daily_summary AS (
              SELECT
                DATE(entry_time) AS trade_date,
                symbol,
                strategy,
                timeframe,
                SUM(profit - fees) AS net_profit_after_fees
              FROM `{self.project_id}.{self.dataset_id}.{self.trades_table_id}`
              WHERE run_name = '{run_name}'
              GROUP BY trade_date, symbol, strategy, timeframe
            ),

            with_lags AS (
              SELECT
                *,
                LAG(net_profit_after_fees, 1) OVER (PARTITION BY symbol, strategy, timeframe ORDER BY trade_date) AS np_day_1_ago,
                LAG(net_profit_after_fees, 2) OVER (PARTITION BY symbol, strategy, timeframe ORDER BY trade_date) AS np_day_2_ago,
                LAG(net_profit_after_fees, 3) OVER (PARTITION BY symbol, strategy, timeframe ORDER BY trade_date) AS np_day_3_ago, 
                LAG(net_profit_after_fees, 4) OVER (PARTITION BY symbol, strategy, timeframe ORDER BY trade_date) AS np_day_4_ago,
                LAG(net_profit_after_fees, 5) OVER (PARTITION BY symbol, strategy, timeframe ORDER BY trade_date) AS np_day_5_ago
              FROM daily_summary
            )

            SELECT
              symbol,
              strategy,
              timeframe,
              CONCAT(symbol, ' - ', strategy, ' - ', timeframe) AS combination,
              net_profit_after_fees,
              np_day_1_ago,
              np_day_2_ago,
              np_day_3_ago,
              np_day_4_ago,
              np_day_5_ago
            FROM with_lags
            WHERE np_day_1_ago > 0 
              AND np_day_2_ago > 0 
              AND np_day_3_ago > 0 
              AND np_day_4_ago > 0 
              AND np_day_5_ago > 0
            ORDER BY net_profit_after_fees DESC
            """
            
            logger.info(f"Querying profitable combinations for {run_name} with {streak_days}-day streaks")
            
            # Execute query
            query_job = self.client.query(query)
            results = query_job.result()
            
            # Convert to list of dictionaries
            profitable_combinations = []
            for row in results:
                profitable_combinations.append({
                    'symbol': row.symbol,
                    'strategy': row.strategy,
                    'timeframe': row.timeframe,
                    'combination': row.combination,
                    'net_profit_after_fees': float(row.net_profit_after_fees) if row.net_profit_after_fees else 0.0,
                    'np_day_1_ago': float(row.np_day_1_ago) if row.np_day_1_ago else 0.0,
                    'np_day_2_ago': float(row.np_day_2_ago) if row.np_day_2_ago else 0.0,
                    'np_day_3_ago': float(row.np_day_3_ago) if row.np_day_3_ago else 0.0,
                    'np_day_4_ago': float(row.np_day_4_ago) if row.np_day_4_ago else 0.0,
                    'np_day_5_ago': float(row.np_day_5_ago) if row.np_day_5_ago else 0.0
                })
            
            logger.info(f"Found {len(profitable_combinations)} combinations with {streak_days}-day profit streaks")
            return profitable_combinations
            
        except Exception as e:
            logger.error(f"Error getting profitable combinations: {e}")
            return [] 