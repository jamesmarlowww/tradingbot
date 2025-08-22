"""
PostgreSQL database operations for trading data
"""

import os
import psycopg2
import psycopg2.extras
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
import time

from config.postgres_config import (
    DATABASE_URL, TRADES_TABLE, DAILY_SUMMARY_TABLE, PERFORMANCE_METRICS_TABLE,
    BATCH_SIZE, MAX_RETRIES, RETRY_DELAY, LOG_QUERIES, LOG_DATA
)

logger = logging.getLogger(__name__)

# Determine the run name (e.g., 'backTestBot', 'testBot', 'prodBot')
RUN_NAME = os.getenv('RUN_NAME', 'backTestBot')

class PostgresDatabase:
    def __init__(self):
        """Initialize PostgreSQL connection"""
        self.connection_string = DATABASE_URL
        self._test_connection()
        logger.info("Successfully connected to PostgreSQL database")

    def _test_connection(self):
        """Test database connection"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()
                    logger.info(f"Connected to PostgreSQL: {version[0]}")
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL: {str(e)}")
            raise

    @contextmanager
    def _get_connection(self):
        """Get database connection with automatic cleanup"""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def _execute_with_retry(self, query: str, params: tuple = None, fetch: bool = False):
        """Execute query with retry logic"""
        for attempt in range(MAX_RETRIES):
            try:
                with self._get_connection() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                        if LOG_QUERIES:
                            logger.debug(f"Executing query: {query}")
                            if params:
                                logger.debug(f"Parameters: {params}")
                        
                        cursor.execute(query, params)
                        
                        if fetch:
                            result = cursor.fetchall()
                            conn.commit()
                            return result
                        else:
                            conn.commit()
                            return cursor.rowcount
                            
            except psycopg2.OperationalError as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Database connection error (attempt {attempt + 1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"Failed to execute query after {MAX_RETRIES} attempts: {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"Error executing query: {str(e)}")
                raise

    def _prepare_trade_data(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare trade data for database insertion"""
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
            'run_name': RUN_NAME
        }
        
        return prepared_data

    def batch_upload_trades(self, trades_data: List[Dict[str, Any]], batch_size: int = BATCH_SIZE) -> int:
        """
        Upload multiple trades in batches to PostgreSQL.
        
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
        
        logger.info(f"Starting batch upload of {total_trades} trades to PostgreSQL")
        
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
                
                # Insert batch using executemany
                query = f"""
                    INSERT INTO {TRADES_TABLE} (
                        entry_time, exit_time, strategy, symbol, timeframe, 
                        trade_type, entry_price, position_size, stop_loss, 
                        take_profit, profit, fees, run_name
                    ) VALUES (
                        %(entry_time)s, %(exit_time)s, %(strategy)s, %(symbol)s, %(timeframe)s,
                        %(trade_type)s, %(entry_price)s, %(position_size)s, %(stop_loss)s,
                        %(take_profit)s, %(profit)s, %(fees)s, %(run_name)s
                    )
                """
                
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        psycopg2.extras.execute_batch(cursor, query, batch_data)
                        conn.commit()
                
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
        Add a single trade record to PostgreSQL.
        
        Args:
            trade_data (dict): Trade information
            
        Returns:
            int: ID of the inserted trade
        """
        try:
            prepared_trade = self._prepare_trade_data(trade_data)
            
            query = f"""
                INSERT INTO {TRADES_TABLE} (
                    entry_time, exit_time, strategy, symbol, timeframe, 
                    trade_type, entry_price, position_size, stop_loss, 
                    take_profit, profit, fees, run_name
                ) VALUES (
                    %(entry_time)s, %(exit_time)s, %(strategy)s, %(symbol)s, %(timeframe)s,
                    %(trade_type)s, %(entry_price)s, %(position_size)s, %(stop_loss)s,
                    %(take_profit)s, %(profit)s, %(fees)s, %(run_name)s
                ) RETURNING id
            """
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, prepared_trade)
                    trade_id = cursor.fetchone()[0]
                    conn.commit()
            
            logger.info(f"Successfully added trade for {trade_data['symbol']} with ID: {trade_id}")
            return trade_id
            
        except Exception as e:
            logger.error(f"Error adding trade: {str(e)}")
            raise

    def get_trades(self, filters: Optional[Dict[str, Any]] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Retrieve trades from PostgreSQL.
        
        Args:
            filters (dict, optional): Filters to apply
            limit (int): Maximum number of trades to return
            
        Returns:
            list: List of trade dictionaries
        """
        try:
            query = f"SELECT * FROM {TRADES_TABLE}"
            params = []
            
            if filters:
                conditions = []
                for field, value in filters.items():
                    conditions.append(f"{field} = %s")
                    params.append(value)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            query += f" ORDER BY entry_time DESC LIMIT {limit}"
            
            result = self._execute_with_retry(query, tuple(params), fetch=True)
            
            # Convert to list of dictionaries
            trades = [dict(row) for row in result]
            
            logger.info(f"Retrieved {len(trades)} trades from database")
            return trades
            
        except Exception as e:
            logger.error(f"Error retrieving trades: {str(e)}")
            raise

    def clear_trades(self, run_name: Optional[str] = None) -> int:
        """
        Clear trades from the database.
        
        Args:
            run_name (str, optional): Only clear trades from specific run
            
        Returns:
            int: Number of trades deleted
        """
        try:
            if run_name:
                query = f"DELETE FROM {TRADES_TABLE} WHERE run_name = %s"
                deleted_count = self._execute_with_retry(query, (run_name,))
            else:
                query = f"DELETE FROM {TRADES_TABLE}"
                deleted_count = self._execute_with_retry(query)
            
            logger.info(f"Cleared {deleted_count} trades from database")
            return deleted_count
            
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
        Get performance summary from trades.
        
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
                FROM {TRADES_TABLE}
                WHERE profit IS NOT NULL
            """
            
            params = []
            if start_date:
                query += " AND entry_time >= %s"
                params.append(start_date)
            if end_date:
                query += " AND entry_time <= %s"
                params.append(end_date)
            
            query += " GROUP BY symbol, strategy, timeframe ORDER BY total_profit DESC"
            
            result = self._execute_with_retry(query, tuple(params), fetch=True)
            df = pd.DataFrame(result)
            
            logger.info(f"Generated performance summary with {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Error generating performance summary: {str(e)}")
            raise

    def save_daily_summary(self, daily_summary: List[Dict[str, Any]]) -> int:
        """
        Save daily summary data to database.
        
        Args:
            daily_summary (list): List of daily summary dictionaries
            
        Returns:
            int: Number of records saved
        """
        if not daily_summary:
            return 0
        
        try:
            query = f"""
                INSERT INTO {DAILY_SUMMARY_TABLE} (
                    date, symbol, strategy, timeframe, trades_count, 
                    total_profit, winning_trades, losing_trades, win_rate
                ) VALUES (
                    %(date)s, %(symbol)s, %(strategy)s, %(timeframe)s, %(trades_count)s,
                    %(total_profit)s, %(winning_trades)s, %(losing_trades)s, %(win_rate)s
                ) ON CONFLICT (date, symbol, strategy, timeframe) 
                DO UPDATE SET
                    trades_count = EXCLUDED.trades_count,
                    total_profit = EXCLUDED.total_profit,
                    winning_trades = EXCLUDED.winning_trades,
                    losing_trades = EXCLUDED.losing_trades,
                    win_rate = EXCLUDED.win_rate
            """
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    psycopg2.extras.execute_batch(cursor, query, daily_summary)
                    conn.commit()
            
            logger.info(f"Saved {len(daily_summary)} daily summary records")
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
            tables = [TRADES_TABLE, DAILY_SUMMARY_TABLE, PERFORMANCE_METRICS_TABLE]
            for table in tables:
                query = f"SELECT COUNT(*) FROM {table}"
                result = self._execute_with_retry(query, fetch=True)
                stats[f"{table}_count"] = result[0][0] if result else 0
            
            # Get latest trade date
            query = f"SELECT MAX(entry_time) FROM {TRADES_TABLE}"
            result = self._execute_with_retry(query, fetch=True)
            stats['latest_trade_date'] = result[0][0] if result and result[0][0] else None
            
            # Get total profit
            query = f"SELECT SUM(profit) FROM {TRADES_TABLE} WHERE profit IS NOT NULL"
            result = self._execute_with_retry(query, fetch=True)
            stats['total_profit'] = result[0][0] if result and result[0][0] else 0
            
            logger.info(f"Database stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            raise 