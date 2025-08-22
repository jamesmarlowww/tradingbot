"""
Shared core functionality for all trading bots
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
import time
from typing import Dict, List, Any, Optional, Tuple

from binance.client import Client
from config.config import API_KEY, API_SECRET, TESTNET, INITIAL_BALANCE
from config.automation_config import *
from trading.strategies import *
from utils.indicators import calculate_rsi, calculate_ema, calculate_macd, calculate_bollinger_bands, calculate_atr
from scripts.helpers.backtest_utils import prepare_data, calculate_position_size, calculate_fee_adjusted_profit, check_stop_loss_take_profit
from scripts.helpers.performance_utils import generate_performance_report, save_trade_history, load_trade_history
from scripts.helpers.trade_utils import execute_trade, update_open_positions
from utils.bigquery_database import BigQueryDatabase

logger = logging.getLogger(__name__)

class BotCore:
    """Shared core functionality for all trading bots"""
    
    def __init__(self, bot_type: str, run_name: str):
        """
        Initialize the bot core
        
        Args:
            bot_type: 'backtest', 'test', or 'prod'
            run_name: Name for this bot run (e.g., 'backTestBot', 'testBot', 'prodBot')
        """
        self.bot_type = bot_type
        self.run_name = run_name
        self.client = None
        self.db = BigQueryDatabase()
        
        # Initialize Binance client for live bots
        if bot_type in ['test', 'prod', 'monitor']:
            self.client = Client(API_KEY, API_SECRET, testnet=TESTNET)
            if TESTNET:
                self.client.API_URL = "https://testnet.binance.vision/api"
        
        # Automation state
        self.automation_state = {
            'trading_enabled': True,
            'last_check_time': 0,
            'current_streak': 0,
            'streak_history': []
        }
        
        # Performance tracking
        self.initial_balance = INITIAL_BALANCE
        self.current_balance = INITIAL_BALANCE
        self.peak_balance = INITIAL_BALANCE
        self.max_drawdown = 0
        
        # Trade history
        self.trade_history = {}
        
        logger.info(f"Initialized {bot_type} bot core for {run_name}")

    def get_strategy_instance(self, strategy_name: str, **kwargs):
        """Get a strategy instance with default parameters"""
        strategy_map = {
            'RSIStrategy': RSIStrategy,
            'EnhancedRSIStrategy': EnhancedRSIStrategy,
            'RSIDivergenceStrategy': RSIDivergenceStrategy,
            'MovingAverageCrossover': MovingAverageCrossover,
            'BollingerBandStrategy': BollingerBandStrategy,
            'MomentumStrategy': MomentumStrategy,
            'TrendFollowingStrategy': TrendFollowingStrategy,
            'LiveReactiveRSIStrategy': LiveReactiveRSIStrategy,
            'VWAPStrategy': VWAPStrategy,
            'PriceActionBreakoutStrategy': PriceActionBreakoutStrategy
        }
        
        if strategy_name not in strategy_map:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        # Standard parameter names that all bots can use
        standard_params = {
            'rsi_period': 14,
            'oversold_threshold': 30,
            'overbought_threshold': 70,
            'short_period': 10,
            'long_period': 20,
            'period': 20,
            'std_dev': 2,
            'threshold': 0.001,
            'volatility_factor': 0.01,
            'trend_period': 50,
            'divergence_threshold': 0.1,
            'breakout_period': 20
        }
        
        # Strategy-specific parameter mappings
        strategy_param_mappings = {
            'RSIStrategy': {
                'rsi_period': 'rsi_period',
                'oversold_threshold': 'oversold',
                'overbought_threshold': 'overbought'
            },
            'EnhancedRSIStrategy': {
                'rsi_period': 'rsi_period',
                'oversold_threshold': 'oversold_threshold',
                'overbought_threshold': 'overbought_threshold',
                'volatility_factor': 'volatility_factor',
                'trend_period': 'trend_period'
            },
            'RSIDivergenceStrategy': {
                'rsi_period': 'rsi_period',
                'divergence_threshold': 'divergence_threshold'
            },
            'MovingAverageCrossover': {
                'short_period': 'short_window',
                'long_period': 'long_window'
            },
            'BollingerBandStrategy': {
                'period': 'period',
                'std_dev': 'std_dev'
            },
            'MomentumStrategy': {
                'period': 'period'
            },
            'TrendFollowingStrategy': {
                'short_period': 'short_period',
                'long_period': 'long_period',
                'threshold': 'threshold'
            },
            'LiveReactiveRSIStrategy': {
                'rsi_period': 'rsi_period',
                'oversold_threshold': 'oversold_threshold',
                'overbought_threshold': 'overbought_threshold',
                'volatility_factor': 'volatility_factor'
            },
            'VWAPStrategy': {
                'period': 'period'
            },
            'PriceActionBreakoutStrategy': {
                'breakout_period': 'breakout_period'
            }
        }
        
        # Start with standard parameters
        params = standard_params.copy()
        
        # Override with any provided kwargs
        params.update(kwargs)
        
        # Map to strategy-specific parameter names
        mapping = strategy_param_mappings[strategy_name]
        strategy_params = {}
        
        for standard_name, strategy_name_param in mapping.items():
            if standard_name in params:
                strategy_params[strategy_name_param] = params[standard_name]
        
        return strategy_map[strategy_name](**strategy_params)

    def fetch_market_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Fetch market data for a symbol and timeframe"""
        try:
            # Map timeframe strings to Binance intervals
            interval_map = {
                '1m': Client.KLINE_INTERVAL_1MINUTE,
                '5m': Client.KLINE_INTERVAL_5MINUTE,
                '15m': Client.KLINE_INTERVAL_15MINUTE,
                '30m': Client.KLINE_INTERVAL_30MINUTE,
                '1h': Client.KLINE_INTERVAL_1HOUR,
                '2h': Client.KLINE_INTERVAL_2HOUR,
                '4h': Client.KLINE_INTERVAL_4HOUR,
                '6h': Client.KLINE_INTERVAL_6HOUR,
                '8h': Client.KLINE_INTERVAL_8HOUR,
                '12h': Client.KLINE_INTERVAL_12HOUR,
                '1d': Client.KLINE_INTERVAL_1DAY,
                '3d': Client.KLINE_INTERVAL_3DAY,
                '1w': Client.KLINE_INTERVAL_1WEEK,
                '1M': Client.KLINE_INTERVAL_1MONTH
            }
            
            interval = interval_map.get(timeframe, Client.KLINE_INTERVAL_1HOUR)
            
            if self.bot_type == 'backtest':
                # For backtest, use historical data
                klines = self.client.get_historical_klines(symbol, interval, limit=limit)
            else:
                # For live bots, use current data
                klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            
            # Create DataFrame
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                             'close_time', 'quote_asset_volume', 'trades', 
                                             'taker_buy_base', 'taker_buy_quote', 'ignored'])
            
            # Convert types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            # Convert timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return pd.DataFrame()

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for the dataframe"""
        try:
            df['rsi'] = calculate_rsi(df['close'])
            df['ema_12'] = calculate_ema(df['close'], 12)
            df['ema_26'] = calculate_ema(df['close'], 26)
            df['macd'], df['macd_signal'], df['macd_histogram'] = calculate_macd(df['close'])
            df['bb_upper'], df['bb_middle'], df['bb_lower'] = calculate_bollinger_bands(df['close'])
            df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
            
            return df
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df

    def generate_signals(self, df: pd.DataFrame, strategy_name: str, **strategy_params) -> pd.DataFrame:
        """Generate trading signals using the specified strategy"""
        try:
            # Check if DataFrame has required data
            if df.empty:
                logger.warning(f"Empty DataFrame provided to {strategy_name}")
                return pd.DataFrame()
            
            # Check for required columns
            required_columns = ['close', 'rsi']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing required columns for {strategy_name}: {missing_columns}")
                return pd.DataFrame()
            
            strategy = self.get_strategy_instance(strategy_name, **strategy_params)
            signals = strategy.generate_signals(df)
            return signals
        except Exception as e:
            logger.error(f"Error generating signals for {strategy_name}: {e}")
            return pd.DataFrame()

    def check_streak_conditions(self) -> bool:
        """Check if trading should be enabled based on streak conditions"""
        # Emergency override - force trading enabled
        if EMERGENCY_OVERRIDE:
            if not self.automation_state['trading_enabled']:
                self.automation_state['trading_enabled'] = True
                logger.warning("🟡 EMERGENCY OVERRIDE: Trading forced enabled")
            return True
        
        if not STREAK_AUTOMATION_ENABLED:
            return True
        
        current_time = time.time()
        
        # Only check once per day
        if current_time - self.automation_state['last_check_time'] < AUTOMATION_CHECK_INTERVAL:
            return self.automation_state['trading_enabled']
        
        self.automation_state['last_check_time'] = current_time
        
        # Calculate daily profit for the last N days
        daily_profits = []
        today = datetime.now().date()
        
        for i in range(REQUIRED_POSITIVE_DAYS):
            check_date = today - timedelta(days=i+1)
            daily_profit = self.calculate_daily_profit(check_date)
            daily_profits.append(daily_profit)
        
        # Check if we have required consecutive positive days
        positive_days = sum(1 for profit in daily_profits if profit > MIN_PROFIT_THRESHOLD)
        
        # Update streak tracking
        self.automation_state['current_streak'] = positive_days
        self.automation_state['streak_history'].append({
            'date': today.isoformat(),
            'streak': positive_days,
            'daily_profits': daily_profits
        })
        
        # Keep only last N days of history
        if len(self.automation_state['streak_history']) > MAX_STREAK_HISTORY_DAYS:
            self.automation_state['streak_history'] = self.automation_state['streak_history'][-MAX_STREAK_HISTORY_DAYS:]
        
        # Enable trading if we have the required positive days
        should_enable = positive_days >= REQUIRED_POSITIVE_DAYS
        
        if should_enable != self.automation_state['trading_enabled']:
            self.automation_state['trading_enabled'] = should_enable
            if should_enable:
                logger.info(f"🟢 TRADING ENABLED: {positive_days} consecutive positive days detected")
                if VERBOSE_STREAK_LOGGING:
                    logger.info(f"Daily profits: {daily_profits}")
            else:
                logger.warning(f"🔴 TRADING DISABLED: Only {positive_days} positive days (need {REQUIRED_POSITIVE_DAYS})")
                if VERBOSE_STREAK_LOGGING:
                    logger.info(f"Daily profits: {daily_profits}")
        
        return should_enable

    def calculate_daily_profit(self, date: datetime.date) -> float:
        """Calculate total profit for a specific date from BigQuery"""
        try:
            # Query BigQuery for trades on the specific date
            start_datetime = datetime.combine(date, datetime.min.time())
            end_datetime = datetime.combine(date, datetime.max.time())
            
            # Get trades from BigQuery for the date range
            filters = {
                'start_date': start_datetime,
                'end_date': end_datetime,
                'run_name': self.run_name
            }
            
            trades = self.db.get_trades(filters=filters, limit=None)
            
            # Calculate total profit for the day
            total_profit = sum(trade.get('profit', 0.0) for trade in trades)
            
            if VERBOSE_STREAK_LOGGING and trades:
                logger.info(f"Found {len(trades)} trades on {date}, total profit: ${total_profit:.2f}")
            
            return total_profit
            
        except Exception as e:
            logger.warning(f"Failed to get daily profit from BigQuery for {date}: {e}")
            return 0.0

    def save_trade_to_bigquery(self, trade_data: Dict[str, Any]):
        """Save a completed trade to BigQuery"""
        try:
            # Prepare trade data for BigQuery
            bigquery_trade = {
                'entry_time': trade_data.get('entry_time'),
                'exit_time': trade_data.get('exit_time'),
                'strategy': trade_data.get('strategy'),
                'symbol': trade_data.get('symbol'),
                'timeframe': trade_data.get('timeframe'),
                'trade_type': trade_data.get('trade_type', 'LONG'),
                'entry_price': trade_data.get('entry_price'),
                'exit_price': trade_data.get('exit_price'),
                'position_size': trade_data.get('position_size'),
                'profit': trade_data.get('profit', 0.0),
                'fees': trade_data.get('fees', 0.0),
                'run_name': self.run_name
            }
            
            self.db.add_trade(bigquery_trade)
            logger.info(f"Saved trade to BigQuery: {trade_data.get('symbol')} - ${trade_data.get('profit', 0):.2f}")
            
        except Exception as e:
            logger.error(f"Error saving trade to BigQuery: {e}")

    def save_signal_to_bigquery(self, signal_data: Dict[str, Any]):
        """Save a trading signal to BigQuery for monitoring purposes"""
        try:
            # Prepare signal data for BigQuery
            bigquery_signal = {
                'timestamp': signal_data.get('timestamp'),
                'symbol': signal_data.get('symbol'),
                'strategy': signal_data.get('strategy'),
                'timeframe': signal_data.get('timeframe'),
                'signal_type': signal_data.get('signal'),
                'price': signal_data.get('price'),
                'run_name': self.run_name
            }
            
            # Use the daily_summary table for signals
            self.db.save_daily_summary([bigquery_signal])
            logger.info(f"Saved signal to BigQuery: {signal_data.get('symbol')} - {signal_data.get('signal')}")
            
        except Exception as e:
            logger.error(f"Error saving signal to BigQuery: {e}")

    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        try:
            # Get all trades for this bot run
            filters = {'run_name': self.run_name}
            trades = self.db.get_trades(filters=filters, limit=None)
            
            if not trades:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'win_rate': 0.0,
                    'total_profit': 0.0,
                    'avg_profit_per_trade': 0.0,
                    'max_drawdown': 0.0,
                    'sharpe_ratio': 0.0
                }
            
            # Calculate basic metrics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.get('profit', 0) > 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            total_profit = sum(t.get('profit', 0) for t in trades)
            avg_profit_per_trade = total_profit / total_trades if total_trades > 0 else 0
            
            # Calculate drawdown
            running_balance = self.initial_balance
            peak_balance = self.initial_balance
            max_drawdown = 0
            
            for trade in sorted(trades, key=lambda x: x.get('entry_time')):
                running_balance += trade.get('profit', 0)
                if running_balance > peak_balance:
                    peak_balance = running_balance
                drawdown = (peak_balance - running_balance) / peak_balance
                max_drawdown = max(max_drawdown, drawdown)
            
            # Calculate Sharpe ratio (simplified)
            profits = [t.get('profit', 0) for t in trades]
            if len(profits) > 1:
                avg_return = np.mean(profits)
                std_return = np.std(profits)
                sharpe_ratio = avg_return / std_return if std_return > 0 else 0
            else:
                sharpe_ratio = 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'avg_profit_per_trade': avg_profit_per_trade,
                'max_drawdown': max_drawdown * 100,  # Convert to percentage
                'sharpe_ratio': sharpe_ratio
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}

    def display_performance_summary(self):
        """Display comprehensive performance summary"""
        metrics = self.calculate_performance_metrics()
        
        print(f"\n=== {self.run_name.upper()} PERFORMANCE SUMMARY ===")
        print(f"{'Metric':<25} {'Value':<15}")
        print("-" * 40)
        print(f"{'Total Trades':<25} {metrics.get('total_trades', 0):<15}")
        print(f"{'Winning Trades':<25} {metrics.get('winning_trades', 0):<15}")
        print(f"{'Win Rate':<25} {metrics.get('win_rate', 0):<15.2f}%")
        print(f"{'Total Profit':<25} ${metrics.get('total_profit', 0):<15.2f}")
        print(f"{'Avg Profit/Trade':<25} ${metrics.get('avg_profit_per_trade', 0):<15.2f}")
        print(f"{'Max Drawdown':<25} {metrics.get('max_drawdown', 0):<15.2f}%")
        print(f"{'Sharpe Ratio':<25} {metrics.get('sharpe_ratio', 0):<15.2f}")
        
        # Display automation status
        if STREAK_AUTOMATION_ENABLED:
            status = "🟢 ENABLED" if self.automation_state['trading_enabled'] else "🔴 DISABLED"
            print(f"{'Trading Status':<25} {status:<15}")
            print(f"{'Current Streak':<25} {self.automation_state['current_streak']}/{REQUIRED_POSITIVE_DAYS}<15")

    def run_daily_monitor(self, trading_combinations: List[Tuple[str, str, str]], 
                         monitor_interval: int = 3600) -> None:
        """
        Run daily monitoring mode - analyzes market and records potential trades
        
        Args:
            trading_combinations: List of (symbol, strategy, timeframe) tuples to monitor
            monitor_interval: How often to check (in seconds)
        """
        logger.info(f"Starting daily monitor mode for {len(trading_combinations)} combinations")
        
        while True:
            try:
                current_time = datetime.now()
                logger.info(f"Daily monitor check at {current_time}")
                
                # Check streak conditions
                trading_enabled = self.check_streak_conditions()
                
                # Analyze all combinations
                for symbol, strategy_name, timeframe in trading_combinations:
                    try:
                        # Fetch market data
                        df = self.fetch_market_data(symbol, timeframe)
                        if df.empty:
                            continue
                        
                        # Calculate indicators
                        df = self.calculate_indicators(df)
                        
                        # Generate signals
                        signals = self.generate_signals(df, strategy_name)
                        
                        if not signals.empty:
                            latest_signal = signals.iloc[-1]
                            
                            # Record the analysis (even if not trading)
                            analysis_record = {
                                'timestamp': current_time,
                                'symbol': symbol,
                                'strategy': strategy_name,
                                'timeframe': timeframe,
                                'signal': 'BUY' if latest_signal.get('position', 0) > 0 else 'SELL' if latest_signal.get('position', 0) < 0 else 'NEUTRAL',
                                'price': df['close'].iloc[-1],
                                'trading_enabled': trading_enabled,
                                'run_name': self.run_name
                            }
                            
                            # Save analysis to BigQuery (for tracking purposes)
                            self.db.save_daily_summary([analysis_record])
                            
                            if trading_enabled:
                                logger.info(f"✅ {symbol} - {strategy_name} - {analysis_record['signal']} signal detected")
                            else:
                                logger.info(f"📊 {symbol} - {strategy_name} - {analysis_record['signal']} signal (trading disabled)")
                    
                    except Exception as e:
                        logger.error(f"Error analyzing {symbol}/{strategy_name}: {e}")
                        continue
                
                # Display performance summary
                self.display_performance_summary()
                
                # Wait for next check
                logger.info(f"Next monitor check in {monitor_interval/3600:.1f} hours")
                time.sleep(monitor_interval)
                
            except KeyboardInterrupt:
                logger.info("Daily monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in daily monitor: {e}")
                time.sleep(60)  # Wait 1 minute before retrying 