#!/usr/bin/env python3
"""
Smart Backtest Script - Focuses on most profitable combinations
with optimized risk management and fee handling
"""

import os
import sys
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_database import BigQueryDatabase
from scripts.helpers.backtest_utils import prepare_data, calculate_fee_adjusted_profit, should_close_trade_for_minimum_profit
from trading.strategies import *
from trading.execution import BacktestExecutor
import ccxt

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set environment variable for bot type
os.environ['RUN_NAME'] = 'smartBacktest'

class SmartBacktest:
    def __init__(self):
        self.db = BigQueryDatabase()
        self.exchange = ccxt.binance({
            'apiKey': '',
            'secret': '',
            'sandbox': True,
            'enableRateLimit': True
        })
        
        # Most profitable combinations from previous results
        self.target_combinations = [
            ('BNBUSDT', 'EnhancedRSIStrategy', '15m'),
            ('BTCUSDT', 'EnhancedRSIStrategy', '30m'),
            ('BTCUSDT', 'LiveReactiveRSIStrategy', '1h'),
            ('BTCUSDT', 'EnhancedRSIStrategy', '15m'),
            ('DOGEUSDT', 'EnhancedRSIStrategy', '15m'),
            ('BNBUSDT', 'MomentumStrategy', '15m'),
            ('BNBUSDT', 'EnhancedRSIStrategy', '30m'),
            ('BNBUSDT', 'TrendFollowingStrategy', '15m'),
            ('DOTUSDT', 'LiveReactiveRSIStrategy', '2h'),
            ('XRPUSDT', 'MomentumStrategy', '30m'),
        ]
        
        # Strategy mapping
        self.strategy_map = {
            'RSIStrategy': RSIStrategy,
            'EnhancedRSIStrategy': EnhancedRSIStrategy,
            'LiveReactiveRSIStrategy': LiveReactiveRSIStrategy,
            'RSIDivergenceStrategy': RSIDivergenceStrategy,
            'MovingAverageCrossover': MovingAverageCrossover,
            'BollingerBandStrategy': BollingerBandStrategy,
            'MomentumStrategy': MomentumStrategy,
            'TrendFollowingStrategy': TrendFollowingStrategy
        }
    
    def fetch_historical_data(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """Fetch historical data with error handling"""
        try:
            logger.info(f"Fetching {limit} candles for {symbol} at {timeframe}")
            
            # Convert timeframe to ccxt format
            tf_map = {'15m': '15m', '30m': '30m', '1h': '1h', '2h': '2h', '4h': '4h', '1d': '1d'}
            ccxt_timeframe = tf_map.get(timeframe, '1h')
            
            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(symbol, ccxt_timeframe, limit=limit)
            
            if not ohlcv:
                logger.warning(f"No data received for {symbol} at {timeframe}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"Successfully fetched {len(df)} candles for {symbol} at {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol} at {timeframe}: {e}")
            return pd.DataFrame()
    
    def run_smart_backtest(self):
        """Run backtest on most profitable combinations"""
        logger.info("Starting Smart Backtest on most profitable combinations")
        
        all_trades = []
        total_trades_uploaded = 0
        
        for symbol, strategy_name, timeframe in self.target_combinations:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {symbol} - {strategy_name} - {timeframe}")
            logger.info(f"{'='*60}")
            
            # Fetch data
            df = self.fetch_historical_data(symbol, timeframe, limit=2000)
            if df.empty:
                logger.warning(f"No data available for {symbol} using {strategy_name} at {timeframe}")
                continue
            
            # Prepare data
            df = prepare_data(df)
            if df.empty:
                logger.warning(f"Failed to prepare data for {symbol}")
                continue
            
            # Initialize strategy
            strategy_class = self.strategy_map.get(strategy_name)
            if not strategy_class:
                logger.error(f"Unknown strategy: {strategy_name}")
                continue
            
            strategy = strategy_class()
            
            # Generate signals
            signals = strategy.generate_signals(df)
            if signals.empty:
                logger.warning(f"No signals generated for {symbol} using {strategy_name}")
                continue
            
            # Run backtest with smart execution
            trades = self.run_smart_execution(df, signals, symbol, strategy_name, timeframe)
            
            if trades:
                all_trades.extend(trades)
                total_trades_uploaded += len(trades)
                logger.info(f"Generated {len(trades)} trades for {symbol} - {strategy_name} - {timeframe}")
                
                # Upload to BigQuery
                self.upload_trades_to_bigquery(trades)
        
        # Final summary
        logger.info(f"\n{'='*60}")
        logger.info("SMART BACKTEST SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total combinations processed: {len(self.target_combinations)}")
        logger.info(f"Total trades generated: {len(all_trades)}")
        logger.info(f"Total trades uploaded to BigQuery: {total_trades_uploaded}")
        
        if all_trades:
            total_profit = sum(trade['profit'] for trade in all_trades)
            total_fees = sum(trade.get('fees', 0) for trade in all_trades)
            net_profit = total_profit - total_fees
            
            logger.info(f"Total gross profit: ${total_profit:.2f}")
            logger.info(f"Total fees: ${total_fees:.2f}")
            logger.info(f"Net profit: ${net_profit:.2f}")
            
            # Save results
            self.save_results(all_trades)
    
    def run_smart_execution(self, df: pd.DataFrame, signals: pd.DataFrame, symbol: str, 
                           strategy_name: str, timeframe: str) -> List[Dict[str, Any]]:
        """Run smart execution with better risk management"""
        trades = []
        open_positions = []
        balance = 10000  # Starting balance
        
        for i in range(len(df)):
            current_price = df['close'].iloc[i]
            current_time = df.index[i]
            
            # Check for exit signals on open positions
            positions_to_close = []
            for pos in open_positions:
                # Check stop loss and take profit
                stop_loss_hit, take_profit_hit = self.check_stop_loss_take_profit(pos, current_price)
                
                # Check minimum profit threshold (to avoid fee erosion)
                min_profit_hit = should_close_trade_for_minimum_profit(pos, current_price, min_profit_pct=0.008)
                
                if stop_loss_hit or take_profit_hit or min_profit_hit:
                    positions_to_close.append(pos)
            
            # Close positions
            for pos in positions_to_close:
                closed_trade = self.close_position(pos, current_price, current_time, symbol, strategy_name, timeframe)
                if closed_trade:
                    trades.append(closed_trade)
                    balance += closed_trade['profit']
                open_positions.remove(pos)
            
            # Check for new entry signals
            if signals['signal'].iloc[i] != 0 and len(open_positions) < 3:  # Max 3 concurrent positions
                # Calculate position size (5% of balance per trade)
                position_size = (balance * 0.05) / current_price
                
                trade_type = 'LONG' if signals['signal'].iloc[i] > 0 else 'SHORT'
                
                # Calculate stop loss and take profit
                if trade_type == 'LONG':
                    stop_loss = current_price * 0.98  # 2% stop loss
                    take_profit = current_price * 1.06  # 6% take profit
                else:
                    stop_loss = current_price * 1.02  # 2% stop loss
                    take_profit = current_price * 0.94  # 6% take profit
                
                # Create new position
                position = {
                    'symbol': symbol,
                    'type': trade_type,
                    'entry_price': current_price,
                    'entry_time': current_time,
                    'position_size': position_size,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'strategy': strategy_name,
                    'timeframe': timeframe
                }
                
                open_positions.append(position)
                logger.info(f"Opened {trade_type} position for {symbol} at {current_price}")
        
        # Close any remaining positions at the end
        for pos in open_positions:
            closed_trade = self.close_position(pos, df['close'].iloc[-1], df.index[-1], 
                                             symbol, strategy_name, timeframe)
            if closed_trade:
                trades.append(closed_trade)
        
        return trades
    
    def close_position(self, position: Dict[str, Any], exit_price: float, exit_time: pd.Timestamp,
                      symbol: str, strategy_name: str, timeframe: str) -> Dict[str, Any]:
        """Close a position and calculate profit/loss"""
        entry_price = position['entry_price']
        position_size = position['position_size']
        trade_type = position['type']
        
        # Calculate gross profit/loss
        if trade_type == 'LONG':
            gross_profit = (exit_price - entry_price) * position_size
        else:  # SHORT
            gross_profit = (entry_price - exit_price) * position_size
        
        # Calculate fees and net profit
        net_profit, fees = calculate_fee_adjusted_profit({
            'entry_price': entry_price,
            'exit_price': exit_price,
            'position_size': position_size,
            'type': trade_type
        })
        
        # Determine exit reason
        if exit_price <= position['stop_loss'] and trade_type == 'LONG':
            exit_reason = 'stop_loss'
        elif exit_price >= position['stop_loss'] and trade_type == 'SHORT':
            exit_reason = 'stop_loss'
        elif exit_price >= position['take_profit'] and trade_type == 'LONG':
            exit_reason = 'take_profit'
        elif exit_price <= position['take_profit'] and trade_type == 'SHORT':
            exit_reason = 'take_profit'
        else:
            exit_reason = 'manual'
        
        return {
            'symbol': symbol,
            'type': trade_type,
            'entry_price': entry_price,
            'entry_time': position['entry_time'],
            'position_size': position_size,
            'strategy': strategy_name,
            'timeframe': timeframe,
            'stop_loss': position['stop_loss'],
            'take_profit': position['take_profit'],
            'exit_price': exit_price,
            'exit_time': exit_time,
            'profit': net_profit,  # Net profit after fees
            'fees': fees,
            'exit_reason': exit_reason,
            'run_name': os.environ.get('RUN_NAME', 'smartBacktest')
        }
    
    def check_stop_loss_take_profit(self, position: Dict[str, Any], current_price: float) -> tuple:
        """Check if stop loss or take profit has been hit"""
        entry_price = position['entry_price']
        trade_type = position['type']
        
        if trade_type == 'LONG':
            stop_loss = position['stop_loss']
            take_profit = position['take_profit']
            return current_price <= stop_loss, current_price >= take_profit
        else:  # SHORT
            stop_loss = position['stop_loss']
            take_profit = position['take_profit']
            return current_price >= stop_loss, current_price <= take_profit
    
    def upload_trades_to_bigquery(self, trades: List[Dict[str, Any]]):
        """Upload trades to BigQuery"""
        if not trades:
            return
        
        try:
            logger.info(f"Uploading {len(trades)} trades to BigQuery")
            self.db.add_trades(trades)
            logger.info(f"Successfully uploaded {len(trades)} trades to BigQuery")
        except Exception as e:
            logger.error(f"Error uploading trades to BigQuery: {e}")
    
    def save_results(self, trades: List[Dict[str, Any]]):
        """Save results to CSV and JSON"""
        if not trades:
            return
        
        # Save to CSV
        df_trades = pd.DataFrame(trades)
        csv_path = 'output/smart_backtest_trades.csv'
        df_trades.to_csv(csv_path, index=False)
        logger.info(f"Saved {len(trades)} trades to {csv_path}")
        
        # Save to JSON
        import json
        json_path = 'output/smart_backtest_trades.json'
        with open(json_path, 'w') as f:
            json.dump(trades, f, indent=2, default=str)
        logger.info(f"Saved {len(trades)} trades to {json_path}")

if __name__ == "__main__":
    smart_backtest = SmartBacktest()
    smart_backtest.run_smart_backtest() 