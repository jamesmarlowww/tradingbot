"""
Firestore database operations for trading data
"""

import os
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account
import pandas as pd
import logging
from config.firestore_config import (
    FIRESTORE_PROJECT_ID,
    FIRESTORE_CREDENTIALS_PATH,
    DEFAULT_TIMEZONE,
    DEFAULT_DECIMAL_PLACES,
    TRADES_COLLECTION
)

logger = logging.getLogger(__name__)

# Determine the run name (e.g., 'backTestBot', 'testBot', 'prodBot')
RUN_NAME = os.getenv('RUN_NAME', 'backTestBot')

class TradingDatabase:
    def __init__(self):
        """Initialize Firestore client"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                FIRESTORE_CREDENTIALS_PATH
            )
            self.db = firestore.Client(
                project=FIRESTORE_PROJECT_ID,
                credentials=credentials
            )
            logger.info("Successfully connected to Firestore")
        except Exception as e:
            logger.error(f"Error connecting to Firestore: {str(e)}")
            raise

    def _convert_to_timestamp(self, dt):
        """Convert datetime to Firestore timestamp"""
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
        return firestore.SERVER_TIMESTAMP if dt is None else firestore.Timestamp.from_datetime(dt)

    def _prepare_trade_data(self, trade_data):
        """Prepare trade data for Firestore with proper timestamps and trade type"""
        # Convert timestamps
        entry_time = self._convert_to_timestamp(trade_data['entry_time'])
        exit_time = self._convert_to_timestamp(trade_data['exit_time'])
        
        # Determine if this is a buy or sell record
        is_buy = trade_data['trade_type'].upper() == 'LONG'
        
        # Prepare the trade data
        prepared_data = {
            'entry_time': entry_time,
            'exit_time': exit_time,
            'strategy': trade_data['strategy'],
            'symbol': trade_data['symbol'],
            'timeframe': trade_data['timeframe'],
            'trade_type': trade_data['trade_type'],
            'is_buy': is_buy,  # Add explicit buy/sell flag
            'entry_price': trade_data['entry_price'],
            'position_size': trade_data['position_size'],
            'stop_loss': trade_data['stop_loss'],
            'take_profit': trade_data['take_profit'],
            'profit': trade_data.get('profit', 0),
            'fees': trade_data.get('fees', 0),
            'timestamp': firestore.SERVER_TIMESTAMP,
            'run_name': RUN_NAME  # Add run name to track which bot generated the trade
        }
        
        return prepared_data

    def batch_upload_trades(self, trades_data, collection_name=TRADES_COLLECTION, batch_size=500):
        """
        Upload multiple trades in batches to Firestore.
        
        Args:
            trades_data (list): List of trade dictionaries to upload
            collection_name (str): Name of the Firestore collection to use
            batch_size (int): Number of trades to upload in each batch (default: 500)
        """
        try:
            total_trades = len(trades_data)
            if total_trades == 0:
                logger.info("No trades to upload")
                return

            logger.info(f"Starting batch upload of {total_trades} trades to {collection_name}")
            
            # Process trades in batches
            for i in range(0, total_trades, batch_size):
                batch = trades_data[i:i + batch_size]
                current_batch = i // batch_size + 1
                total_batches = (total_trades + batch_size - 1) // batch_size
                
                try:
                    # Create a new batch
                    batch_write = self.db.batch()
                    
                    # Add trades to batch
                    for trade in batch:
                        # Prepare trade data with proper timestamps
                        prepared_trade = self._prepare_trade_data(trade)
                        
                        # Create new document reference
                        doc_ref = self.db.collection(collection_name).document()
                        
                        # Add to batch
                        batch_write.set(doc_ref, prepared_trade)
                    
                    # Commit the batch
                    batch_write.commit()
                    
                    logger.info(f"Successfully uploaded batch {current_batch}/{total_batches} ({len(batch)} trades)")
                    
                except Exception as batch_error:
                    logger.error(f"Error uploading batch {current_batch}: {str(batch_error)}")
                    # Continue with next batch even if this one fails
                    continue
            
            logger.info(f"Completed batch upload of {total_trades} trades to {collection_name}")
            
        except Exception as e:
            logger.error(f"Error in batch_upload_trades: {str(e)}")
            raise

    def add_trade(self, trade_data, collection_name=TRADES_COLLECTION):
        """
        Add a single trade record to Firestore.
        For multiple trades, use batch_upload_trades instead.
        
        Args:
            trade_data (dict): Trade information
            collection_name (str): Name of the Firestore collection to use
        """
        try:
            # Prepare trade data with proper timestamps
            prepared_trade = self._prepare_trade_data(trade_data)
            
            # Add to specified collection
            trade_ref = self.db.collection(collection_name).document()
            trade_ref.set(prepared_trade)
            
            logger.info(f"Successfully added trade for {trade_data['symbol']} to collection {collection_name}")
            return trade_ref.id
            
        except Exception as e:
            logger.error(f"Error adding trade to {collection_name}: {str(e)}")
            raise

    def update_trade(self, trade_id, update_data, collection_name=TRADES_COLLECTION):
        """
        Update an existing trade record.
        
        Args:
            trade_id (str): ID of the trade to update
            update_data (dict): Fields to update
            collection_name (str): Name of the Firestore collection to use
        """
        try:
            # Convert any datetime fields to Firestore timestamps
            for field in ['entry_time', 'exit_time']:
                if field in update_data:
                    update_data[field] = self._convert_to_timestamp(update_data[field])
            
            trade_ref = self.db.collection(collection_name).document(trade_id)
            trade_ref.update(update_data)
            logger.info(f"Successfully updated trade {trade_id} in collection {collection_name}")
        except Exception as e:
            logger.error(f"Error updating trade in {collection_name}: {str(e)}")
            raise

    def get_trades(self, filters=None, collection_name=TRADES_COLLECTION):
        """
        Get trades with optional filters.
        
        Args:
            filters (dict): Dictionary of field: value pairs to filter by
            collection_name (str): Name of the Firestore collection to use
        """
        try:
            query = self.db.collection(collection_name)
            logger.info(f"Querying collection: {collection_name}")
            
            if filters:
                logger.info(f"Applying filters: {filters}")
                for field, value in filters.items():
                    query = query.where(field, '==', value)
            
            docs = query.stream()
            logger.info(f"Found {len(list(docs))} documents in query")
            
            trades = [doc.to_dict() for doc in docs]
            logger.info(f"Converted {len(trades)} documents to dictionaries")
            
            return trades
        except Exception as e:
            logger.error(f"Error getting trades from {collection_name}: {str(e)}")
            raise

    def export_to_csv(self, filters=None, filename=None, collection_name=TRADES_COLLECTION):
        """
        Export trades to CSV.
        
        Args:
            filters (dict, optional): Filters to apply
            filename (str, optional): Output filename
            collection_name (str): Name of the Firestore collection to use
        """
        try:
            data = []
            query = self.db.collection(collection_name)
            if filters:
                for field, value in filters.items():
                    query = query.where(field, '==', value)
            
            for doc in query.stream():
                data.append(doc.to_dict())
            
            df = pd.DataFrame(data)
            if filename:
                df.to_csv(filename, index=False)
            return df
        except Exception as e:
            logger.error(f"Error exporting to CSV from {collection_name}: {str(e)}")
            raise

    def clear_trades(self, collection_name=TRADES_COLLECTION):
        """
        Clear all trades from the specified Firestore collection.
        Uses batch processing to handle large numbers of trades efficiently.
        
        Args:
            collection_name (str): Name of the Firestore collection to clear
        """
        try:
            # Get all trades
            trades = self.db.collection(collection_name).stream()
            trade_refs = [trade.reference for trade in trades]
            
            if not trade_refs:
                logger.info(f"No trades to clear from {collection_name}")
                return
                
            logger.info(f"Found {len(trade_refs)} trades to clear from {collection_name}")
            
            # Process in batches of 500 (Firestore batch limit)
            batch_size = 500
            total_batches = (len(trade_refs) + batch_size - 1) // batch_size
            
            for i in range(0, len(trade_refs), batch_size):
                batch = trade_refs[i:i + batch_size]
                current_batch = i // batch_size + 1
                
                try:
                    # Create a new batch
                    batch_write = self.db.batch()
                    
                    # Add delete operations to batch
                    for ref in batch:
                        batch_write.delete(ref)
                    
                    # Commit the batch
                    batch_write.commit()
                    
                    logger.info(f"Successfully cleared batch {current_batch}/{total_batches} ({len(batch)} trades) from {collection_name}")
                    
                except Exception as batch_error:
                    logger.error(f"Error clearing batch {current_batch} from {collection_name}: {str(batch_error)}")
                    # Continue with next batch even if this one fails
                    continue
                    
            logger.info(f"Completed clearing trades from {collection_name}. Processed {len(trade_refs)} trades in {total_batches} batches")
            
        except Exception as e:
            logger.error(f"Error in clear_trades for {collection_name}: {str(e)}")
            raise

    def analyze_trades(self, collection_name=TRADES_COLLECTION):
        """
        Analyze the trades collection to identify potential bloat and data patterns.
        
        Args:
            collection_name (str): Name of the Firestore collection to analyze
        """
        try:
            trades = self.get_trades(collection_name=collection_name)
            if not trades:
                logger.info(f"No trades found in collection {collection_name}")
                return
                
            # Initialize counters
            total_trades = len(trades)
            trade_types = {}
            strategies = {}
            symbols = {}
            timeframes = {}
            
            # Analyze each trade
            for trade in trades:
                # Count trade types
                trade_type = trade.get('trade_type', 'unknown')
                trade_types[trade_type] = trade_types.get(trade_type, 0) + 1
                
                # Count strategies
                strategy = trade.get('strategy', 'unknown')
                strategies[strategy] = strategies.get(strategy, 0) + 1
                
                # Count symbols
                symbol = trade.get('symbol', 'unknown')
                symbols[symbol] = symbols.get(symbol, 0) + 1
                
                # Count timeframes
                timeframe = trade.get('timeframe', 'unknown')
                timeframes[timeframe] = timeframes.get(timeframe, 0) + 1
            
            # Log analysis results
            logger.info(f"\nAnalysis of collection {collection_name}:")
            logger.info(f"Total number of trades: {total_trades}")
            
            logger.info("\nTrade Types Distribution:")
            for trade_type, count in trade_types.items():
                logger.info(f"  {trade_type}: {count} ({count/total_trades*100:.2f}%)")
            
            logger.info("\nStrategies Distribution:")
            for strategy, count in strategies.items():
                logger.info(f"  {strategy}: {count} ({count/total_trades*100:.2f}%)")
            
            logger.info("\nSymbols Distribution:")
            for symbol, count in symbols.items():
                logger.info(f"  {symbol}: {count} ({count/total_trades*100:.2f}%)")
            
            logger.info("\nTimeframes Distribution:")
            for timeframe, count in timeframes.items():
                logger.info(f"  {timeframe}: {count} ({count/total_trades*100:.2f}%)")
            
            # Check for potential bloat
            logger.info("\nPotential Bloat Analysis:")
            
            # Check for trades with missing required fields
            required_fields = ['entry_time', 'exit_time', 'strategy', 'symbol', 'timeframe', 'trade_type']
            missing_fields = {field: 0 for field in required_fields}
            
            for trade in trades:
                for field in required_fields:
                    if field not in trade or trade[field] is None:
                        missing_fields[field] += 1
            
            logger.info("\nMissing Required Fields:")
            for field, count in missing_fields.items():
                if count > 0:
                    logger.info(f"  {field}: {count} trades missing ({count/total_trades*100:.2f}%)")
            
            # Check for trades with unusual values
            unusual_trades = []
            for trade in trades:
                # Check for zero or negative profits
                if trade.get('profit', 0) <= 0:
                    unusual_trades.append(f"Trade {trade.get('symbol')} has zero/negative profit")
                
                # Check for missing timestamps
                if not trade.get('entry_time') or not trade.get('exit_time'):
                    unusual_trades.append(f"Trade {trade.get('symbol')} has missing timestamps")
                
                # Check for unusual position sizes
                if trade.get('position_size', 0) <= 0:
                    unusual_trades.append(f"Trade {trade.get('symbol')} has invalid position size")
            
            if unusual_trades:
                logger.info("\nUnusual Trades Found:")
                for issue in unusual_trades:
                    logger.info(f"  {issue}")
            
            return {
                'total_trades': total_trades,
                'trade_types': trade_types,
                'strategies': strategies,
                'symbols': symbols,
                'timeframes': timeframes,
                'missing_fields': missing_fields,
                'unusual_trades': unusual_trades
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trades in {collection_name}: {str(e)}")
            raise 