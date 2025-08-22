#!/usr/bin/env python3
"""
Profit Streak Bot - Only trades after 5 consecutive profitable days
Uses shared BotCore for maximum code reuse
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
os.environ['RUN_NAME'] = 'profitStreakBot'

# Detect production environment
IS_PRODUCTION = os.environ.get('ENVIRONMENT', 'development') == 'production'

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root_dir)

from utils.bot_core import BotCore
from config.config import INITIAL_BALANCE

# Configure logging for production
if IS_PRODUCTION:
    log_dir = '/var/log/tradingbot'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'profitstreakbot.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
else:
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

# Register signal handlers and cleanup
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
atexit.register(cleanup)

class ProfitStreakBot:
    """Bot that only trades after 5 consecutive profitable days"""
    
    def __init__(self, run_name: str = 'profitStreakBot', initial_balance: float = INITIAL_BALANCE):
        self.run_name = run_name
        self.initial_balance = initial_balance
        self.bot_core = BotCore(bot_type='profit_streak', run_name=run_name)
        self.is_running = False
        self.last_check_time = 0
        
        # Trading state
        self.balance = initial_balance
        self.open_positions = []
        self.trades = []
        
        # Streak tracking
        self.consecutive_profitable_days = 0
        self.required_profitable_days = 5
        self.last_daily_check = None
        self.profitable_combinations = []
        
        # Import combinations from backTestBot
        from scripts.bots.backTestBot import BACKTEST_COMBOS
        self.trading_combinations = BACKTEST_COMBOS
    
    def check_profit_streak(self) -> bool:
        """Check if we have combinations with 5 consecutive profitable days"""
        try:
            # Get combinations with 5-day profit streaks from BigQuery
            profitable_combinations = self.bot_core.db.get_profitable_combinations(
                run_name='monitorBot',  # Check monitorBot's performance
                streak_days=5
            )
            
            if not profitable_combinations:
                logger.info("No combinations with 5-day profit streaks found")
                return False
            
            # Store the profitable combinations for trading
            self.profitable_combinations = profitable_combinations
            self.consecutive_profitable_days = len(profitable_combinations)
            
            logger.info(f"✅ PROFIT STREAK ACHIEVED! Found {len(profitable_combinations)} combinations with 5-day profit streaks")
            logger.info(f"Profitable combinations: {[combo['combination'] for combo in profitable_combinations[:5]]}...")
            return True
                
        except Exception as e:
            logger.error(f"Error checking profit streak: {e}")
            return False
    
    def run_profit_streak_trading(self, trading_interval: int = 900):  # 15 minutes
        """Run trading only when profit streak is achieved"""
        logger.info("Starting Profit Streak Bot")
        logger.info(f"Required profitable days: {self.required_profitable_days}")
        logger.info(f"Trading interval: {trading_interval} seconds ({trading_interval/60:.1f} minutes)")
        logger.info(f"Trading combinations: {len(self.trading_combinations)}")
        
        self.is_running = True
        self.last_check_time = time.time()
        
        try:
            consecutive_errors = 0
            max_consecutive_errors = 5 if IS_PRODUCTION else 1
            
            while self.is_running and not shutdown_requested:
                current_time = time.time()
                
                # Check if it's time for the next cycle
                if current_time - self.last_check_time >= trading_interval:
                    try:
                        logger.info(f"=== PROFIT STREAK TRADING CYCLE ===")
                        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # Check profit streak (only once per day)
                        current_date = datetime.now().date()
                        if self.last_daily_check != current_date:
                            self.last_daily_check = current_date
                            streak_achieved = self.check_profit_streak()
                        else:
                            streak_achieved = self.consecutive_profitable_days >= self.required_profitable_days
                        
                        if streak_achieved:
                            logger.info("🚀 PROFIT STREAK ACTIVE - TRADING ENABLED")
                            # Use only the combinations that have 5-day profit streaks
                            profitable_combos = [(combo['symbol'], combo['strategy'], combo['timeframe']) 
                                               for combo in self.profitable_combinations]
                            self._run_trading_cycle(profitable_combos)
                        else:
                            logger.info("⏸️ Waiting for profit streak - trading disabled")
                        
                        # Reset error counter on successful cycle
                        consecutive_errors = 0
                        
                        # Update last check time
                        self.last_check_time = current_time
                        
                        logger.info(f"Completed trading cycle")
                        logger.info(f"Next cycle in {trading_interval} seconds")
                        logger.info("=" * 50)
                        
                    except Exception as e:
                        consecutive_errors += 1
                        logger.error(f"Error in trading cycle {consecutive_errors}/{max_consecutive_errors}: {e}")
                        
                        if consecutive_errors >= max_consecutive_errors:
                            logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping bot")
                            self.is_running = False
                            break
                        
                        # Wait before retrying
                        logger.info(f"Waiting 60 seconds before retry...")
                        time.sleep(60)
                        continue
                
                # Sleep for a short interval
                time.sleep(10)
                
                # Show "still alive" message every 5 minutes
                if int(current_time) % 300 == 0:
                    logger.info(f"💓 Profit Streak Bot still alive - waiting for next cycle...")
                
        except KeyboardInterrupt:
            logger.info("Profit Streak Bot stopped by user")
            self.is_running = False
        except Exception as e:
            logger.error(f"Critical error in profit streak bot: {e}")
            self.is_running = False
            if IS_PRODUCTION:
                logger.error("Bot will be restarted by systemd")
            else:
                raise
    
    def _run_trading_cycle(self, combinations: List[Tuple[str, str, str]]):
        """Run a single trading cycle with live trading execution"""
        try:
            current_time = datetime.now()
            logger.info(f"🔄 PROFIT STREAK TRADING CYCLE STARTED at {current_time}")
            logger.info(f"📊 Checking {len(combinations)} combinations...")
            
            signals_found = 0
            trades_executed = 0
            
            # Determine which timeframes should be checked based on current time
            current_minute = current_time.minute
            current_hour = current_time.hour
            
            timeframe_checks = {
                '15m': True,
                '30m': current_minute % 30 == 0,
                '1h': current_minute == 0,
                '2h': current_minute == 0 and current_hour % 2 == 0,
                '4h': current_minute == 0 and current_hour % 4 == 0,
                '1d': current_minute == 0 and current_hour == 0,
            }
            
            active_timeframes = [tf for tf, should_check in timeframe_checks.items() if should_check]
            logger.info(f"⏰ Active timeframes for this cycle: {', '.join(active_timeframes)}")
            
            # Fetch latest market data and analyze
            for i, (symbol, strategy_name, timeframe) in enumerate(combinations, 1):
                try:
                    # Skip combinations that shouldn't be checked at this time
                    if not timeframe_checks.get(timeframe, True):
                        continue
                    
                    # Fetch market data
                    df = self.bot_core.fetch_market_data(symbol, timeframe, limit=100)
                    if df.empty:
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
                            
                            # Execute trade
                            self._execute_live_trade(symbol, strategy_name, timeframe, latest_row, current_time, latest_signal)
                            trades_executed += 1
                    
                    # Update open positions
                    if self.open_positions:
                        self._update_live_positions(latest_row, current_time)
                    
                    # Progress indicator every 10 combinations
                    if i % 10 == 0:
                        logger.info(f"📈 Progress: {i}/{len(combinations)} combinations checked...")
                    
                except Exception as e:
                    logger.error(f"❌ Error trading {symbol} {strategy_name} {timeframe}: {e}")
                    continue
            
            # Summary for this cycle
            logger.info(f"✅ PROFIT STREAK TRADING CYCLE COMPLETED at {datetime.now()}")
            logger.info(f"📊 Summary: {signals_found} signals found, {trades_executed} trades executed")
            
        except Exception as e:
            logger.error(f"❌ Error in profit streak trading cycle: {e}")
    
    def _execute_live_trade(self, symbol, strategy_name, timeframe, row, timestamp, signal):
        """Execute a live trade"""
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
            logger.info(f"✅ PROFIT STREAK TRADE EXECUTED: {symbol} {strategy_name} {timeframe}")
            logger.info(f"   💰 Entry Price: ${row['close']:.4f}")
            logger.info(f"   📊 Position Size: {position_size:.4f}")
            logger.info(f"   🎯 Type: {trade_direction}")
            logger.info(f"   📈 Open Positions: {len(self.open_positions)}")
            
        except Exception as e:
            logger.error(f"❌ Error executing profit streak trade: {e}")
    
    def _update_live_positions(self, row, timestamp):
        """Update open positions and handle closed trades"""
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
                
                logger.info(f"💰 PROFIT STREAK TRADE CLOSED: {closed_trade['symbol']} {closed_trade['strategy']}")
                logger.info(f"   💰 Entry: ${closed_trade['entry_price']:.4f} | Exit: ${closed_trade['exit_price']:.4f}")
                logger.info(f"   📊 Profit: ${closed_trade['profit']:.2f} | Fees: ${closed_trade['fees']:.2f}")
                logger.info(f"   💵 Balance: ${self.balance:.2f}")
            
            # Remove closed positions from open positions
            self.open_positions = [pos for pos in self.open_positions if pos not in closed_positions]
            
        except Exception as e:
            logger.error(f"❌ Error updating profit streak positions: {e}")
    
    def stop(self):
        """Stop the profit streak bot"""
        self.is_running = False
        logger.info("Profit Streak Bot stopping...")

def main():
    """Main function to run the profit streak bot"""
    parser = argparse.ArgumentParser(description='Profit Streak Bot - Trade only after 5 profitable days')
    parser.add_argument('--interval', type=int, default=900,
                        help='Trading interval in seconds (default: 900 = 15 minutes)')
    parser.add_argument('--run-name', default='profitStreakBot',
                        help='Run name for BigQuery (default: profitStreakBot)')
    
    args = parser.parse_args()
    
    # Initialize profit streak bot
    profit_streak_bot = ProfitStreakBot(run_name=args.run_name)
    
    try:
        profit_streak_bot.run_profit_streak_trading(args.interval)
    except KeyboardInterrupt:
        logger.info("Profit Streak Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running profit streak bot: {e}")
        raise

if __name__ == "__main__":
    main()
