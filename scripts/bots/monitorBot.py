#!/usr/bin/env python3
"""
Daily Monitor Bot - Monitors trading performance and can execute trades on active schedules
Uses shared BotCore for maximum code reuse with other bots
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
import time
from typing import List, Tuple, Optional
import signal
import atexit

# Set the run name for BigQuery
os.environ['RUN_NAME'] = 'monitorBot'

# Detect production environment
IS_PRODUCTION = os.environ.get('ENVIRONMENT', 'development') == 'production'

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root_dir)

from utils.bot_core import BotCore
from config.config import INITIAL_BALANCE

# Configure logging for production
if IS_PRODUCTION:
    # Production logging - write to file
    log_dir = '/var/log/tradingbot'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'monitorbot.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
else:
    # Development logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True

def cleanup():
    """Cleanup function for graceful shutdown"""
    logger.info("Performing cleanup...")
    # Add any cleanup logic here

# Register signal handlers and cleanup
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
atexit.register(cleanup)

# ===== MONITOR BOT CONFIGURATION =====
# Import the same comprehensive combinations as backTestBot
from scripts.bots.backTestBot import BACKTEST_COMBOS

# Use all backtest combinations for comprehensive monitoring
DEFAULT_MONITOR_COMBOS = BACKTEST_COMBOS

# Schedule configurations - All combinations monitored on every cycle
SCHEDULE_CONFIGS = {
    '15m': {
        'interval': 15 * 60,  # 15 minutes in seconds
        'combinations': DEFAULT_MONITOR_COMBOS,  # Monitor ALL combinations
        'description': 'Comprehensive monitoring of all combinations every 15 minutes'
    },
    '30m': {
        'interval': 30 * 60,  # 30 minutes in seconds
        'combinations': DEFAULT_MONITOR_COMBOS,  # Monitor ALL combinations
        'description': 'Comprehensive monitoring of all combinations every 30 minutes'
    },
    '1h': {
        'interval': 60 * 60,  # 1 hour in seconds
        'combinations': DEFAULT_MONITOR_COMBOS,  # Monitor ALL combinations
        'description': 'Comprehensive monitoring of all combinations every hour'
    },
    '2h': {
        'interval': 2 * 60 * 60,  # 2 hours in seconds
        'combinations': DEFAULT_MONITOR_COMBOS,  # Monitor ALL combinations
        'description': 'Comprehensive monitoring of all combinations every 2 hours'
    },
    '4h': {
        'interval': 4 * 60 * 60,  # 4 hours in seconds
        'combinations': DEFAULT_MONITOR_COMBOS,  # Monitor ALL combinations
        'description': 'Comprehensive monitoring of all combinations every 4 hours'
    },
    'daily': {
        'interval': 24 * 60 * 60,  # 24 hours in seconds
        'combinations': DEFAULT_MONITOR_COMBOS,  # Monitor ALL combinations
        'description': 'Comprehensive monitoring of all combinations daily'
    },
    'comprehensive': {
        'interval': 60 * 60,  # 1 hour in seconds
        'combinations': DEFAULT_MONITOR_COMBOS,
        'description': 'Comprehensive monitoring of all combinations (hourly)'
    },
    'continuous': {
        'interval': 60,  # 1 minute in seconds
        'combinations': DEFAULT_MONITOR_COMBOS,
        'description': 'Continuous monitoring of all combinations'
    }
}

class MonitorBot:
    """Monitor Bot for daily performance tracking and active trading"""
    
    def __init__(self, run_name: str = 'monitorBot', initial_balance: float = INITIAL_BALANCE):
        self.run_name = run_name
        self.initial_balance = initial_balance
        self.bot_core = BotCore(bot_type='monitor', run_name=run_name)
        self.is_running = False
        self.last_check_time = 0
        
        # Trading state (like backTestBot)
        self.balance = initial_balance
        self.open_positions = []
        self.trades = []
        
    def run_schedule_monitor(self, schedule: str, custom_combinations: Optional[List[Tuple[str, str, str]]] = None):
        """Run monitoring on a specific schedule"""
        if schedule not in SCHEDULE_CONFIGS:
            logger.error(f"Invalid schedule: {schedule}. Available schedules: {list(SCHEDULE_CONFIGS.keys())}")
            return
            
        config = SCHEDULE_CONFIGS[schedule]
        combinations = custom_combinations or config['combinations']
        
        logger.info(f"Starting {config['description']}")
        logger.info(f"Schedule: {schedule} (interval: {config['interval']} seconds)")
        logger.info(f"Monitoring {len(combinations)} combinations")
        
        self.is_running = True
        self.last_check_time = time.time()
        
        try:
            consecutive_errors = 0
            max_consecutive_errors = 5 if IS_PRODUCTION else 1
            
            while self.is_running and not shutdown_requested:
                current_time = time.time()
                
                # Check if it's time for the next monitoring cycle
                if current_time - self.last_check_time >= config['interval']:
                    try:
                        logger.info(f"=== {schedule.upper()} MONITORING CYCLE ===")
                        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # Run monitoring cycle
                        self._run_monitoring_cycle(combinations, schedule)
                        
                        # Reset error counter on successful cycle
                        consecutive_errors = 0
                        
                        # Update last check time
                        self.last_check_time = current_time
                        
                        logger.info(f"Completed {schedule} monitoring cycle")
                        logger.info(f"Next cycle in {config['interval']} seconds")
                        logger.info("=" * 50)
                        
                    except Exception as e:
                        consecutive_errors += 1
                        logger.error(f"Error in monitoring cycle {consecutive_errors}/{max_consecutive_errors}: {e}")
                        
                        if consecutive_errors >= max_consecutive_errors:
                            logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping bot")
                            self.is_running = False
                            break
                        
                        # Wait before retrying
                        logger.info(f"Waiting 60 seconds before retry...")
                        time.sleep(60)
                        continue
                
                # Sleep for a short interval to avoid excessive CPU usage
                time.sleep(10)
                
                # Show "still alive" message every 5 minutes
                if int(current_time) % 300 == 0:  # Every 5 minutes
                    logger.info(f"💓 Monitor bot still alive - waiting for next {schedule} cycle...")
                
        except KeyboardInterrupt:
            logger.info("Monitor bot stopped by user")
            self.is_running = False
        except Exception as e:
            logger.error(f"Critical error in monitor bot: {e}")
            self.is_running = False
            if IS_PRODUCTION:
                # In production, don't raise - let systemd handle restart
                logger.error("Bot will be restarted by systemd")
            else:
                raise
    
    def run_daily_monitor(self, combinations: List[Tuple[str, str, str]], monitor_interval: int = 3600):
        """Run daily monitoring (legacy method for compatibility)"""
        logger.info("Starting daily monitoring mode...")
        self.bot_core.run_daily_monitor(
            trading_combinations=combinations,
            monitor_interval=monitor_interval
        )
    
    def run_active_trading(self, combinations: List[Tuple[str, str, str]], trading_interval: int = 300):
        """Run active trading on specified combinations"""
        logger.info("Starting active trading mode...")
        logger.info(f"Trading interval: {trading_interval} seconds ({trading_interval/60:.1f} minutes)")
        logger.info(f"Trading {len(combinations)} combinations")
        
        self.is_running = True
        self.last_check_time = time.time()
        
        try:
            while self.is_running:
                current_time = time.time()
                
                # Check if it's time for the next trading cycle
                if current_time - self.last_check_time >= trading_interval:
                    logger.info(f"=== ACTIVE TRADING CYCLE ===")
                    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Check streak conditions before trading
                    if self.bot_core.check_streak_conditions():
                        logger.info("✓ Streak conditions met - trading enabled")
                        self._run_trading_cycle(combinations)
                    else:
                        logger.info("✗ Streak conditions not met - trading disabled")
                    
                    # Update last check time
                    self.last_check_time = current_time
                    
                    logger.info(f"Completed trading cycle")
                    logger.info(f"Next cycle in {trading_interval} seconds")
                    logger.info("=" * 50)
                
                # Sleep for a short interval
                time.sleep(10)
                
                # Show "still alive" message every 5 minutes
                if int(current_time) % 300 == 0:  # Every 5 minutes
                    logger.info(f"💓 Trading bot still alive - waiting for next trading cycle...")
                
        except KeyboardInterrupt:
            logger.info("Active trading stopped by user")
            self.is_running = False
        except Exception as e:
            logger.error(f"Error in active trading: {e}")
            self.is_running = False
            raise
    
    def _run_monitoring_cycle(self, combinations: List[Tuple[str, str, str]], schedule: str):
        """Run a single monitoring cycle with live trading execution"""
        try:
            current_time = datetime.now()
            logger.info(f"🔄 LIVE TRADING CYCLE STARTED at {current_time}")
            logger.info(f"📊 Checking {len(combinations)} combinations...")
            
            signals_found = 0
            trades_executed = 0
            
            # Determine which timeframes should be checked based on current time
            current_minute = current_time.minute
            current_hour = current_time.hour
            
            # Define timeframe check intervals
            timeframe_checks = {
                '15m': True,  # Always check 15m combinations
                '30m': current_minute % 30 == 0,  # Check every 30 minutes (at minute 0 and 30)
                '1h': current_minute == 0,  # Check every hour (at minute 0)
                '2h': current_minute == 0 and current_hour % 2 == 0,  # Check every 2 hours
                '4h': current_minute == 0 and current_hour % 4 == 0,  # Check every 4 hours
                '1d': current_minute == 0 and current_hour == 0,  # Check daily at midnight
            }
            
            # Log which timeframes are being checked
            active_timeframes = [tf for tf, should_check in timeframe_checks.items() if should_check]
            logger.info(f"⏰ Active timeframes for this cycle: {', '.join(active_timeframes)}")
            
            # Don't reset trading state - maintain across cycles
            # self.balance = self.initial_balance
            # self.open_positions = []
            
            # Fetch latest market data and analyze
            for i, (symbol, strategy_name, timeframe) in enumerate(combinations, 1):
                try:
                    # Skip combinations that shouldn't be checked at this time
                    if not timeframe_checks.get(timeframe, True):
                        continue
                    
                    # Fetch market data
                    df = self.bot_core.fetch_market_data(symbol, timeframe, limit=100)
                    if df.empty:
                        logger.warning(f"⚠️ No data available for {symbol} {timeframe}")
                        continue
                    
                    # Calculate indicators
                    df = self.bot_core.calculate_indicators(df)
                    
                    # Generate signals
                    signals = self.bot_core.generate_signals(df, strategy_name)
                    
                    # Log current market conditions
                    latest_row = df.iloc[-1]
                    current_price = latest_row['close']
                    current_rsi = latest_row.get('rsi', 'N/A')
                    
                    # Check for trading signals and execute trades
                    if not signals.empty:
                        latest_signal = signals.iloc[-1]
                        
                        # Debug signal structure
                        logger.debug(f"Signal structure: {latest_signal.to_dict()}")
                        
                        # Check for position in the signal
                        position = 0
                        if 'position' in latest_signal:
                            position = latest_signal['position']
                        elif 'signal' in latest_signal:
                            position = latest_signal['signal']
                        
                        if position != 0:
                            signal_type = 'BUY' if position > 0 else 'SELL'
                            signals_found += 1
                            
                            logger.info(f"🎯 SIGNAL DETECTED: {symbol} {timeframe} {strategy_name}")
                            logger.info(f"   💰 Price: ${current_price:.4f}")
                            logger.info(f"   📈 RSI: {current_rsi:.2f}")
                            logger.info(f"   🚦 Signal: {signal_type}")
                            logger.info(f"   📊 Position Value: {position}")
                            
                            # Execute trade like backTestBot
                            self._execute_live_trade(symbol, strategy_name, timeframe, latest_row, current_time, latest_signal)
                            trades_executed += 1
                        else:
                            logger.debug(f"📊 {symbol} {timeframe} {strategy_name}: No signal (position={position})")
                    else:
                        logger.debug(f"📊 {symbol} {timeframe} {strategy_name}: No signals generated")
                            
                    # Update open positions
                    if self.open_positions:
                        self._update_live_positions(latest_row, current_time)
                    
                    # Progress indicator every 10 combinations
                    if i % 10 == 0:
                        logger.info(f"📈 Progress: {i}/{len(combinations)} combinations checked...")
                    
                except Exception as e:
                    logger.error(f"❌ Error monitoring {symbol} {strategy_name} {timeframe}: {e}")
                    continue
            
            # Summary for this cycle
            logger.info(f"✅ LIVE TRADING CYCLE COMPLETED at {datetime.now()}")
            logger.info(f"📊 Summary: {signals_found} signals found, {trades_executed} trades executed")
            
            # Display performance summary
            self.bot_core.display_performance_summary()
            
        except Exception as e:
            logger.error(f"❌ Error in live trading cycle: {e}")
    
    def _execute_live_trade(self, symbol, strategy_name, timeframe, row, timestamp, signal):
        """Execute a live trade like backTestBot"""
        try:
            from scripts.helpers.trade_utils import execute_trade
            from scripts.helpers.backtest_utils import calculate_position_size
            
            # Determine trade direction from signal
            position = 0
            if 'position' in signal:
                position = signal['position']
            elif 'signal' in signal:
                position = signal['signal']
            
            trade_direction = 'LONG' if position > 0 else 'SHORT'
            
            # Calculate position size
            position_size = calculate_position_size(
                row['close'],
                symbol,
                self.balance,
                0.05  # 5% risk per trade
            )
            
            # Execute trade
            trade = execute_trade(
                symbol,
                trade_direction,
                row['close'],
                timestamp,
                strategy_name,
                position_size,
                timeframe,
                0.02,  # 2% stop loss
                0.06   # 6% take profit
            )
            
            # Add to open positions
            self.open_positions.append(trade)
            logger.info(f"✅ LIVE TRADE EXECUTED: {symbol} {strategy_name} {timeframe}")
            logger.info(f"   💰 Entry Price: ${row['close']:.4f}")
            logger.info(f"   📊 Position Size: {position_size:.4f}")
            logger.info(f"   🎯 Type: {trade_direction}")
            logger.info(f"   📈 Open Positions: {len(self.open_positions)}")
            
        except Exception as e:
            logger.error(f"❌ Error executing live trade: {e}")
    
    def _update_live_positions(self, row, timestamp):
        """Update open positions and handle closed trades like backTestBot"""
        try:
            from scripts.helpers.trade_utils import update_open_positions
            from scripts.helpers.backtest_utils import calculate_fee_adjusted_profit
            
            # Update open positions
            closed_positions = update_open_positions(
                self.open_positions,
                row['close'],
                timestamp,
                0.02,  # 2% stop loss
                0.06   # 6% take profit
            )
            
            # Process closed trades
            for closed_trade in closed_positions:
                net_profit, total_fees = calculate_fee_adjusted_profit(closed_trade)
                closed_trade['profit'] = net_profit
                closed_trade['fees'] = total_fees
                self.balance += closed_trade['profit']
                
                # Save completed trade to BigQuery
                trade_data = {
                    'entry_time': closed_trade['entry_time'],
                    'exit_time': closed_trade['exit_time'],
                    'strategy': closed_trade['strategy'],
                    'symbol': closed_trade['symbol'],
                    'timeframe': closed_trade['timeframe'],
                    'trade_type': closed_trade['type'],
                    'entry_price': closed_trade['entry_price'],
                    'exit_price': closed_trade['exit_price'],
                    'position_size': closed_trade['position_size'],
                    'stop_loss': closed_trade['stop_loss'],
                    'take_profit': closed_trade['take_profit'],
                    'profit': closed_trade['profit'],
                    'fees': closed_trade['fees'],
                    'run_name': self.run_name
                }
                
                # Save to BigQuery
                self.bot_core.save_trade_to_bigquery(trade_data)
                
                logger.info(f"💰 TRADE CLOSED: {closed_trade['symbol']} {closed_trade['strategy']}")
                logger.info(f"   💰 Entry: ${closed_trade['entry_price']:.4f} | Exit: ${closed_trade['exit_price']:.4f}")
                logger.info(f"   📊 Profit: ${closed_trade['profit']:.2f} | Fees: ${closed_trade['fees']:.2f}")
                logger.info(f"   💵 Balance: ${self.balance:.2f}")
            
            # Remove closed positions from open positions
            self.open_positions = [pos for pos in self.open_positions if pos not in closed_positions]
            
        except Exception as e:
            logger.error(f"❌ Error updating live positions: {e}")
    
    def _run_trading_cycle(self, combinations: List[Tuple[str, str, str]]):
        """Run a single trading cycle"""
        try:
            for symbol, strategy_name, timeframe in combinations:
                try:
                    # Fetch market data
                    df = self.bot_core.fetch_market_data(symbol, timeframe, limit=100)
                    if df.empty:
                        continue
                    
                    # Calculate indicators
                    df = self.bot_core.calculate_indicators(df)
                    
                    # Generate signals
                    signals = self.bot_core.generate_signals(df, strategy_name)
                    
                    # Check for trading signals
                    if not signals.empty:
                        latest_signal = signals.iloc[-1]
                        if latest_signal in ['BUY', 'SELL']:
                            logger.info(f"Signal detected: {symbol} {strategy_name} {timeframe} - {latest_signal}")
                            
                            # Execute trade (this would be implemented in BotCore)
                            # For now, just log the signal
                            trade_data = {
                                'symbol': symbol,
                                'strategy': strategy_name,
                                'timeframe': timeframe,
                                'signal': latest_signal,
                                'price': df.iloc[-1]['close'],
                                'timestamp': datetime.now(),
                                'run_name': self.run_name
                            }
                            
                            # Save to BigQuery
                            self.bot_core.save_trade_to_bigquery(trade_data)
                            logger.info(f"Trade logged: {trade_data}")
                
                except Exception as e:
                    logger.error(f"Error trading {symbol} {strategy_name} {timeframe}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
    
    def stop(self):
        """Stop the monitor bot"""
        self.is_running = False
        logger.info("Monitor bot stopping...")

def main():
    """Main function to run the monitor bot"""
    parser = argparse.ArgumentParser(description='Monitor Bot - Daily monitoring and active trading')
    parser.add_argument('--mode', choices=['monitor', 'trading'], default='monitor',
                       help='Run mode: monitor (default) or trading (active trading)')
    parser.add_argument('--schedule', choices=list(SCHEDULE_CONFIGS.keys()), default='15m',
                       help='Monitoring schedule (default: 15m)')
    parser.add_argument('--interval', type=int, default=3600,
                       help='Custom interval in seconds (overrides schedule)')
    parser.add_argument('--combinations', nargs='+', 
                       help='Specific combinations to monitor (format: symbol:strategy:timeframe)')
    parser.add_argument('--run-name', default='monitorBot',
                       help='Run name for BigQuery (default: monitorBot)')
    
    args = parser.parse_args()
    
    # Parse custom combinations if provided
    custom_combinations = None
    if args.combinations:
        custom_combinations = []
        for combo in args.combinations:
            try:
                symbol, strategy, timeframe = combo.split(':')
                custom_combinations.append((symbol, strategy, timeframe))
            except ValueError:
                logger.error(f"Invalid combination format: {combo}. Use format: symbol:strategy:timeframe")
                continue
    
    # Initialize monitor bot
    monitor_bot = MonitorBot(run_name=args.run_name)
    
    try:
        if args.mode == 'trading':
            # Active trading mode
            combinations = custom_combinations or DEFAULT_MONITOR_COMBOS
            interval = args.interval if args.interval != 3600 else 300  # Default 5 minutes for trading
            monitor_bot.run_active_trading(combinations, interval)
        else:
            # Monitoring mode
            if args.interval != 3600:
                # Custom interval
                combinations = custom_combinations or DEFAULT_MONITOR_COMBOS
                monitor_bot.run_schedule_monitor('continuous', combinations)
            else:
                # Predefined schedule
                monitor_bot.run_schedule_monitor(args.schedule, custom_combinations)
    
    except KeyboardInterrupt:
        logger.info("Monitor bot stopped by user")
    except Exception as e:
        logger.error(f"Error running monitor bot: {e}")
        raise

if __name__ == "__main__":
    main() 