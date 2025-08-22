import os
import sys

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root_dir)

from binance.client import Client
import pandas as pd
import time
from config.config import API_KEY, API_SECRET, TESTNET, TESTNET_API_URL
from config.automation_config import *
from indicators.moving_averages import calculate_moving_averages
from indicators.momentum import calculate_rsi, calculate_macd
from indicators.volatility import calculate_bollinger_bands, calculate_atr
from indicators.price_action import calculate_price_features
from trading.execution import TradeExecutor
from trading.strategies import RSIStrategy, BollingerBandStrategy, EnhancedRSIStrategy, RSIDivergenceStrategy, TrendFollowingStrategy, LiveReactiveRSIStrategy, MomentumStrategy, VWAPStrategy, PriceActionBreakoutStrategy
import logging
import json
from datetime import datetime, timedelta
import shutil
import glob

# Import shared bot core
from utils.bot_core import BotCore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/logs/trading_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize shared bot core
bot_core = BotCore(bot_type='test', run_name='testBot')

# Keep using Testnet
client = Client(API_KEY, API_SECRET, testnet=TESTNET)
if TESTNET:
    client.API_URL = TESTNET_API_URL

# ===== ACTIVE TRADING CONFIGURATION =====
# Import all combinations from BackTestBot for comprehensive testing
from scripts.bots.backTestBot import BACKTEST_COMBOS

# Use all BackTestBot combinations for comprehensive live testing
ACTIVE_TRADING_COMBOS = BACKTEST_COMBOS

# Extract unique symbols and timeframes
symbols = {combo[0]: combo[0] for combo in ACTIVE_TRADING_COMBOS}
timeframes = {combo[2] for combo in ACTIVE_TRADING_COMBOS}

# Print active configuration
logger.info("\n=== ACTIVE TRADING CONFIGURATION ===")
for symbol, strategy, timeframe in ACTIVE_TRADING_COMBOS:
    logger.info(f"Symbol: {symbol}, Strategy: {strategy}, Timeframe: {timeframe}")
logger.info("===================================\n")

# Risk management parameters - Using same settings as backtest bot
max_position_size = 0.05  # Maximum 5% of balance per position
stop_loss_pct = 0.02     # 2% stop loss
take_profit_pct = 0.06   # 6% take profit
max_risk_per_trade = 0.01  # Maximum 1% risk per trade
max_drawdown_limit = 0.2   # Maximum 20% drawdown

# Initialize account balance tracking
initial_balance = 10000  # Starting balance
current_balance = initial_balance
available_balance = initial_balance
unrealized_pnl = 0
max_drawdown = 0
peak_balance = initial_balance

# Initialize strategies using BotCore (same as BackTestBot)
# This will handle all strategies including the new VWAPStrategy and PriceActionBreakoutStrategy
strategies = {
    'RSIStrategy': RSIStrategy(),
    'RSIDivergenceStrategy': RSIDivergenceStrategy(),
    'EnhancedRSIStrategy': EnhancedRSIStrategy(),
    'LiveReactiveRSIStrategy': LiveReactiveRSIStrategy(),
    'BollingerBandStrategy': BollingerBandStrategy(),
    'MomentumStrategy': MomentumStrategy(),
    'TrendFollowingStrategy': TrendFollowingStrategy(),
    'VWAPStrategy': VWAPStrategy(),
    'PriceActionBreakoutStrategy': PriceActionBreakoutStrategy()
}

# Initialize trade history for all strategies
trade_history = {}
for symbol in symbols.values():
    trade_history[symbol] = {}
    for strategy_name in strategies.keys():
        trade_history[symbol][strategy_name] = {'trades': [], 'profit_usd': 0.0}

# Create trade executors for each symbol
trade_executors = {
    symbol: TradeExecutor(client, symbol, test_mode=False)
    for symbol in symbols.values()
}

def analyze_market():
    """Analyze all combinations using BotCore (same approach as BackTestBot)"""
    try:
        all_data = {}
        all_signals = {}
        
        logger.info(f"🔄 Starting market analysis for {len(ACTIVE_TRADING_COMBOS)} combinations...")
        
        for i, (symbol, strategy_name, timeframe) in enumerate(ACTIVE_TRADING_COMBOS, 1):
            try:
                logger.info(f"📊 Analyzing {symbol} {strategy_name} {timeframe} ({i}/{len(ACTIVE_TRADING_COMBOS)})")
                
                # Use BotCore to fetch market data and generate signals
                df = bot_core.fetch_market_data(symbol, timeframe, limit=100)
                if df.empty:
                    logger.warning(f"⚠️ No data available for {symbol} {timeframe}")
                    continue
                
                # Calculate indicators
                df = bot_core.calculate_indicators(df)
                
                # Generate signals
                signals = bot_core.generate_signals(df, strategy_name)
                
                # Store data and signals
                key = f"{symbol}_{strategy_name}_{timeframe}"
                all_data[key] = df
                all_signals[key] = signals
                
                # Log current market conditions
                if not df.empty:
                    latest_row = df.iloc[-1]
                    current_price = latest_row['close']
                    current_rsi = latest_row.get('rsi', 'N/A')
                    
                    if not signals.empty:
                        latest_signal = signals.iloc[-1]
                        if isinstance(latest_signal, dict) and latest_signal.get('position', 0) != 0:
                            signal_type = 'BUY' if latest_signal['position'] > 0 else 'SELL'
                            logger.info(f"🎯 SIGNAL: {symbol} {timeframe} {strategy_name} - {signal_type} @ ${current_price:.4f} (RSI: {current_rsi:.2f})")
                        else:
                            logger.debug(f"📊 {symbol} {timeframe} {strategy_name}: ${current_price:.4f} (RSI: {current_rsi:.2f}) - No signal")
                    else:
                        logger.debug(f"📊 {symbol} {timeframe} {strategy_name}: ${current_price:.4f} (RSI: {current_rsi:.2f}) - No signals")
                
                # Progress indicator every 10 combinations
                if i % 10 == 0:
                    logger.info(f"📈 Progress: {i}/{len(ACTIVE_TRADING_COMBOS)} combinations analyzed...")
                    
            except Exception as e:
                logger.error(f"❌ Error analyzing {symbol} {strategy_name} {timeframe}: {e}")
                continue
        
        logger.info(f"✅ Market analysis completed - {len(all_data)} combinations processed")
        return all_data, all_signals
        
    except Exception as e:
        logger.error(f"❌ Error in market analysis: {e}")
        return {}, {}

def execute_trades(all_signals, all_data):
    """Execute trades based on signals from all combinations"""
    if not all_signals:
        logger.info("No signals to execute")
        return
    
    logger.info(f"🔄 Executing trades for {len(all_signals)} combinations...")
    
    for key, signals in all_signals.items():
        try:
            # Parse key: "BTCUSDT_RSIStrategy_15m"
            symbol, strategy_name, timeframe = key.split('_', 2)
            
            if signals is None or signals.empty:
                continue
            
            latest_signal = signals.iloc[-1]
            
            # Get current price
            current_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
            
            if latest_signal['position'] > 0:  # Buy signal
                # Calculate position size (1% risk, 2% stop loss)
                quantity = trade_executors[symbol].calculate_position_size(current_price, risk_percent=0.5, stop_loss_percent=2.0)
                
                # Execute buy order
                order = trade_executors[symbol].place_market_order(side='BUY', quantity=quantity)
                
                if order:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    value_usd = current_price * quantity
                    logger.info(f"BUY: {symbol} - {strategy_name} - Price: ${current_price:.2f} - Size: {quantity:.3f} - Value: ${value_usd:.2f}")
                    
                    # Record trade
                    trade_history[symbol][strategy_name]['trades'].append({
                        'timestamp': timestamp,
                        'type': 'BUY',
                        'price': current_price,
                        'quantity': quantity,
                        'value_usd': value_usd,
                        'status': order.get('status', 'TEST')
                    })
                    
                    # Save trade history and display updated performance
                    save_trade_history()
                    display_performance_summary()
                    display_strategy_performance()
                    display_pair_performance()
                    
            elif latest_signal['position'] < 0:  # Sell signal
                quantity = trade_executors[symbol].calculate_position_size(current_price, risk_percent=0.5, stop_loss_percent=2.0)
                
                # Execute sell order
                order = trade_executors[symbol].place_market_order(side='SELL', quantity=quantity)
                
                if order:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    value_usd = current_price * quantity
                    
                    # Calculate P&L if we have previous trades
                    pnl = 0
                    if trade_history[symbol][strategy_name]['trades']:
                        last_buy = None
                        for trade in reversed(trade_history[symbol][strategy_name]['trades']):
                            if trade['type'] == 'BUY':
                                last_buy = trade
                                break
                        
                        if last_buy:
                            buy_price = last_buy['price']
                            buy_qty = last_buy['quantity']
                            
                            if quantity <= buy_qty:
                                pnl = (current_price - buy_price) * quantity
                                trade_history[symbol][strategy_name]['profit_usd'] += pnl
                    
                    logger.info(f"SELL: {symbol} - {strategy_name} - Price: ${current_price:.2f} - Size: {quantity:.3f} - Value: ${value_usd:.2f} - PnL: ${pnl:.2f}")
                    
                    # Record trade
                    trade_history[symbol][strategy_name]['trades'].append({
                        'timestamp': timestamp,
                        'type': 'SELL',
                        'price': current_price,
                        'quantity': quantity,
                        'value_usd': value_usd,
                        'status': order.get('status', 'TEST')
                    })
                    
                    # Save trade history and display updated performance
                    save_trade_history()
                    display_performance_summary()
                    display_strategy_performance()
                    display_pair_performance()
        except Exception as e:
            logger.error(f"❌ Error processing {key}: {e}")
            continue

def save_trade_history():
    """Save trade history to a JSON file with proper error handling"""
    try:
        # Create backup of existing file first
        if os.path.exists('data/history/trade_history.json'):
            backup_path = f'data/history/trade_history_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            shutil.copy2('data/history/trade_history.json', backup_path)
            logger.info(f"Created backup at {backup_path}")
        
        # Create output directory if it doesn't exist
        os.makedirs('data/history', exist_ok=True)
        
        # Calculate current performance metrics
        strategy_performance = calculate_strategy_performance()
        pair_performance = calculate_pair_performance()
        
        # Validate trade history structure
        validated_history = {}
        for symbol, strategies in trade_history.items():
            validated_history[symbol] = {}
            for strategy_name, strategy_data in strategies.items():
                if not isinstance(strategy_data, dict) or 'trades' not in strategy_data:
                    logger.warning(f"Invalid data for {symbol}/{strategy_name}, resetting")
                    validated_history[symbol][strategy_name] = {'trades': [], 'profit_usd': 0.0}
                else:
                    # Validate each trade
                    validated_trades = []
                    for trade in strategy_data['trades']:
                        if not all(k in trade for k in ['timestamp', 'type', 'price', 'quantity', 'value_usd', 'status']):
                            logger.warning(f"Invalid trade data in {symbol}/{strategy_name}, skipping")
                            continue
                        validated_trades.append(trade)
                    validated_history[symbol][strategy_name] = {
                        'trades': validated_trades,
                        'profit_usd': strategy_data.get('profit_usd', 0.0)
                    }
        
        # Prepare save data
        save_data = {
            'trade_history': validated_history,
            'strategy_performance': strategy_performance,
            'pair_performance': pair_performance,
            'last_updated': datetime.now().isoformat()
        }
        
        # Write to temporary file first (atomic operation)
        temp_file = 'data/history/trade_history_temp.json'
        with open(temp_file, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        # Replace the original file (atomic on most filesystems)
        os.replace(temp_file, 'data/history/trade_history.json')
        logger.info("Trade history saved successfully")
        
        # Also save to BigQuery for streak analysis (only new trades)
        try:
            from utils.bigquery_database import BigQueryDatabase
            db = BigQueryDatabase()
            
            # Get existing trades from BigQuery to avoid duplicates
            existing_trades = db.get_trades({'run_name': 'testBot'})
            existing_trade_keys = set()
            
            # Create unique keys for existing trades
            for trade in existing_trades:
                key = f"{trade['symbol']}_{trade['strategy']}_{trade['entry_time']}_{trade['exit_time']}"
                existing_trade_keys.add(key)
            
            # Convert local trade history to BigQuery format (only new trades)
            bigquery_trades = []
            for symbol, strategies in validated_history.items():
                for strategy_name, strategy_data in strategies.items():
                    for trade in strategy_data['trades']:
                        # Only save completed trades (BUY + SELL pairs)
                        if trade['type'] == 'SELL':
                            # Find corresponding BUY trade
                            buy_trade = None
                            for prev_trade in strategy_data['trades']:
                                if prev_trade['type'] == 'BUY' and prev_trade['timestamp'] < trade['timestamp']:
                                    buy_trade = prev_trade
                                    break
                            
                            if buy_trade:
                                # Calculate profit
                                profit = (trade['price'] - buy_trade['price']) * trade['quantity']
                                
                                # Create unique key for this trade
                                trade_key = f"{symbol}_{strategy_name}_{buy_trade['timestamp']}_{trade['timestamp']}"
                                
                                # Only upload if this trade doesn't already exist in BigQuery
                                if trade_key not in existing_trade_keys:
                                    # Prepare BigQuery trade record
                                    bigquery_trade = {
                                        'entry_time': buy_trade['timestamp'],
                                        'exit_time': trade['timestamp'],
                                        'strategy': strategy_name,
                                        'symbol': symbol,
                                        'timeframe': '4h' if symbol in ['ETHUSDT', 'LINKUSDT'] else '1h',
                                        'trade_type': 'LONG',
                                        'entry_price': buy_trade['price'],
                                        'exit_price': trade['price'],
                                        'position_size': buy_trade['quantity'],
                                        'profit': profit,
                                        'fees': (buy_trade['value_usd'] + trade['value_usd']) * 0.001,  # 0.1% fee
                                        'run_name': 'testBot'
                                    }
                                    bigquery_trades.append(bigquery_trade)
            
            # Upload to BigQuery if we have new trades
            if bigquery_trades:
                db.batch_upload_trades(bigquery_trades)
                logger.info(f"Uploaded {len(bigquery_trades)} new completed trades to BigQuery")
            else:
                logger.info("No new trades to upload to BigQuery")
            
        except Exception as e:
            logger.warning(f"Failed to save to BigQuery: {e}")
            # Don't fail the main save operation if BigQuery fails
        
    except Exception as e:
        logger.error(f"Error saving trade history: {e}")
        # Try to restore from backup if save failed
        restore_from_backup()

def load_trade_history():
    """Load trade history with validation and error recovery"""
    try:
        if os.path.exists('data/history/trade_history.json'):
            with open('data/history/trade_history.json', 'r') as f:
                data = json.load(f)
                
                # Validate structure and repair if needed
                validated_history = {}
                for symbol, strategies in data.get('trade_history', {}).items():
                    validated_history[symbol] = {}
                    
                    # Make sure strategies is a dictionary
                    if not isinstance(strategies, dict):
                        logger.warning(f"Invalid strategy data for {symbol}, resetting")
                        validated_history[symbol] = {
                            'EnhancedRSIStrategy': {'trades': [], 'profit_usd': 0.0},
                            'TrendFollowingStrategy': {'trades': [], 'profit_usd': 0.0}
                        }
                        continue
                        
                    for strategy_name, strategy_data in strategies.items():
                        # Ensure strategy data has required structure
                        if not isinstance(strategy_data, dict) or 'trades' not in strategy_data:
                            logger.warning(f"Invalid data for {symbol}/{strategy_name}, resetting")
                            validated_history[symbol][strategy_name] = {'trades': [], 'profit_usd': 0.0}
                        else:
                            # Validate each trade
                            validated_trades = []
                            for trade in strategy_data['trades']:
                                if not all(k in trade for k in ['timestamp', 'type', 'price', 'quantity', 'value_usd', 'status']):
                                    logger.warning(f"Invalid trade data in {symbol}/{strategy_name}, skipping")
                                    continue
                                validated_trades.append(trade)
                            validated_history[symbol][strategy_name] = {
                                'trades': validated_trades,
                                'profit_usd': strategy_data.get('profit_usd', 0.0)
                            }
                
                return validated_history
                
        # Initialize new history if file doesn't exist
        return initialize_empty_trade_history()
    except json.JSONDecodeError:
        logger.error("JSON decode error, attempting to restore from backup")
        return restore_from_backup()
    except Exception as e:
        logger.error(f"Error loading trade history: {e}")
        return initialize_empty_trade_history()

def restore_from_backup():
    """Attempt to restore trade history from the most recent backup"""
    try:
        backup_files = glob.glob('data/history/trade_history_backup_*.json')
        if not backup_files:
            logger.error("No backup files found")
            return initialize_empty_trade_history()
            
        # Get most recent backup
        latest_backup = max(backup_files, key=os.path.getctime)
        logger.info(f"Attempting to restore from backup: {latest_backup}")
        
        with open(latest_backup, 'r') as f:
            data = json.load(f)
            return data.get('trade_history', {})
    except Exception as e:
        logger.error(f"Error restoring from backup: {e}")
        return initialize_empty_trade_history()

def initialize_empty_trade_history():
    """Initialize an empty trade history structure"""
    return {
        'BTCUSDT': {
            'EnhancedRSIStrategy': {'trades': [], 'profit_usd': 0.0},
            'TrendFollowingStrategy': {'trades': [], 'profit_usd': 0.0}
        }
    }

def calculate_portfolio_value():
    """Calculate total portfolio value in USD"""
    try:
        portfolio = {
            'assets': {},
            'total_USD': 0.0
        }
        
        # Get USDT balance
        usdt_balance = trade_executors[symbols['ETH']].get_account_balance('USDT')
        portfolio['assets']['USDT'] = {
            'balance': usdt_balance,
            'value_usd': usdt_balance
        }
        portfolio['total_USD'] += usdt_balance
        
        # Get crypto balances
        for coin, symbol in symbols.items():
            balance = trade_executors[symbol].get_account_balance(coin)
            price = float(client.get_symbol_ticker(symbol=symbol)['price'])
            value_usd = balance * price
            
            portfolio['assets'][coin] = {
                'balance': balance,
                'price': price,
                'value_usd': value_usd
            }
            portfolio['total_USD'] += value_usd
        
        return portfolio
    except Exception as e:
        logger.error(f"Error calculating portfolio value: {e}")
        return None

def calculate_strategy_performance():
    """Calculate and display performance metrics by strategy"""
    strategy_performance = {}
    
    for symbol, strategies in trade_history.items():
        for strategy, data in strategies.items():
            trades = data['trades']
            if trades:
                if strategy not in strategy_performance:
                    strategy_performance[strategy] = {
                        'total_trades': 0,
                        'winning_trades': 0,
                        'realized_profit': 0,
                        'unrealized_profit': 0,
                        'open_positions': 0
                    }
                
                # Count total trades and winning trades
                strategy_performance[strategy]['total_trades'] += len(trades)
                
                # Track open positions and calculate PnL
                open_positions = []
                for trade in trades:
                    if trade['type'] == 'BUY':
                        open_positions.append(trade)
                    elif trade['type'] == 'SELL':
                        # Find matching buy trade
                        if open_positions:
                            buy_trade = open_positions.pop(0)
                            profit = (trade['price'] - buy_trade['price']) * trade['quantity']
                            strategy_performance[strategy]['realized_profit'] += profit
                            if profit > 0:
                                strategy_performance[strategy]['winning_trades'] += 1
                
                # Calculate unrealized profit for remaining open positions
                current_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
                for position in open_positions:
                    unrealized_profit = (current_price - position['price']) * position['quantity']
                    strategy_performance[strategy]['unrealized_profit'] += unrealized_profit
                
                strategy_performance[strategy]['open_positions'] = len(open_positions)
    
    return strategy_performance

def display_strategy_performance():
    """Display performance metrics by strategy in table format"""
    strategy_performance = calculate_strategy_performance()
    
    print("\n=== Strategy Performance ===")
    print(f"{'Strategy':<25} {'Trades':<8} {'Wins':<8} {'Win Rate':<10} {'P&L':<12} {'Open':<8}")
    print("-" * 75)
    
    for strategy, metrics in strategy_performance.items():
        if metrics['total_trades'] > 0:
            win_rate = (metrics['winning_trades'] / metrics['total_trades'] * 100)
            print(f"{strategy:<25} {metrics['total_trades']:<8} {metrics['winning_trades']:<8} "
                  f"{win_rate:<10.2f}% ${metrics['realized_profit']:<12.2f} {metrics['open_positions']:<8}")

def calculate_pair_performance():
    """Calculate and display performance metrics by trading pair"""
    pair_performance = {}
    
    for symbol, strategies in trade_history.items():
        pair_total_trades = 0
        pair_winning_trades = 0
        pair_realized_profit = 0
        pair_unrealized_profit = 0
        pair_open_positions = 0
        
        for strategy, data in strategies.items():
            trades = data['trades']
            if trades:
                pair_total_trades += len(trades)
                
                # Track open positions and calculate PnL
                open_positions = []
                for trade in trades:
                    if trade['type'] == 'BUY':
                        open_positions.append(trade)
                    elif trade['type'] == 'SELL':
                        # Find matching buy trade
                        if open_positions:
                            buy_trade = open_positions.pop(0)
                            profit = (trade['price'] - buy_trade['price']) * trade['quantity']
                            pair_realized_profit += profit
                            if profit > 0:
                                pair_winning_trades += 1
                
                # Calculate unrealized profit for remaining open positions
                current_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
                for position in open_positions:
                    unrealized_profit = (current_price - position['price']) * position['quantity']
                    pair_unrealized_profit += unrealized_profit
                
                pair_open_positions += len(open_positions)
        
        if pair_total_trades > 0:
            pair_performance[symbol] = {
                'total_trades': pair_total_trades,
                'winning_trades': pair_winning_trades,
                'win_rate': (pair_winning_trades / pair_total_trades * 100),
                'realized_profit': pair_realized_profit,
                'unrealized_profit': pair_unrealized_profit,
                'open_positions': pair_open_positions
            }
    
    return pair_performance

def display_pair_performance():
    """Display performance metrics by trading pair in table format"""
    pair_performance = calculate_pair_performance()
    
    print("\n=== Pair Performance ===")
    print(f"{'Pair':<10} {'Trades':<8} {'Wins':<8} {'Win Rate':<10} {'P&L':<12} {'Open':<8}")
    print("-" * 60)
    
    for symbol, metrics in pair_performance.items():
        print(f"{symbol:<10} {metrics['total_trades']:<8} {metrics['winning_trades']:<8} "
              f"{metrics['win_rate']:<10.2f}% ${metrics['realized_profit']:<12.2f} {metrics['open_positions']:<8}")

def calculate_fee_adjusted_profit(trade):
    """Calculate profit after trading fees"""
    if 'profit' not in trade:
        return 0
        
    # Binance spot trading fee is 0.1% per trade (maker or taker)
    fee_rate = 0.001
    
    # Calculate fees for both entry and exit
    entry_value = trade['entry_price'] * trade['position_size']
    exit_value = trade['exit_price'] * trade['position_size']
    
    entry_fee = entry_value * fee_rate
    exit_fee = exit_value * fee_rate
    
    # Calculate profit after fees
    fee_adjusted_profit = trade['profit'] - entry_fee - exit_fee
    
    return fee_adjusted_profit

def update_drawdown():
    """Update maximum drawdown"""
    global peak_balance, max_drawdown
    
    if current_balance > peak_balance:
        peak_balance = current_balance
    
    current_drawdown = (peak_balance - current_balance) / peak_balance
    max_drawdown = max(max_drawdown, current_drawdown)
    
    return current_drawdown <= max_drawdown_limit

def display_performance_summary():
    """Display comprehensive performance summary in table format"""
    # Calculate overall trade performance
    total_trades = 0
    winning_trades = 0
    total_profit = 0
    total_fee_adjusted_profit = 0
    
    for symbol, strategies in trade_history.items():
        for strategy, data in strategies.items():
            trades = data['trades']
            total_trades += len(trades)
            
            for trade in trades:
                if trade.get('profit', 0) > 0:
                    winning_trades += 1
                total_profit += trade.get('profit', 0)
                total_fee_adjusted_profit += calculate_fee_adjusted_profit(trade)
    
    # Account Performance Table
    print("\n=== Account Performance ===")
    print(f"{'Metric':<20} {'Value':<15}")
    print("-" * 35)
    print(f"{'Initial Balance':<20} ${initial_balance:<15.2f}")
    print(f"{'Current Balance':<20} ${current_balance:<15.2f}")
    print(f"{'Available Balance':<20} ${available_balance:<15.2f}")
    print(f"{'Unrealized P&L':<20} ${unrealized_pnl:<15.2f}")
    print(f"{'Total Value':<20} ${(current_balance + unrealized_pnl):<15.2f}")
    print(f"{'Return':<20} {((current_balance - initial_balance) / initial_balance * 100):<15.2f}%")
    print(f"{'Max Drawdown':<20} {max_drawdown:<15.2f}%")
    
    # Trade Performance Table
    print("\n=== Trade Performance ===")
    print(f"{'Metric':<20} {'Value':<15}")
    print("-" * 35)
    print(f"{'Total Trades':<20} {total_trades:<15}")
    print(f"{'Winning Trades':<20} {winning_trades:<15}")
    print(f"{'Win Rate':<20} {(winning_trades/total_trades*100 if total_trades > 0 else 0):<15.2f}%")
    print(f"{'Total Profit':<20} ${total_profit:<15.2f}")
    print(f"{'Profit (After Fees)':<20} ${total_fee_adjusted_profit:<15.2f}")

def check_streak_conditions():
    """Check if trading should be enabled based on streak conditions"""
    return bot_core.check_streak_conditions()

def calculate_daily_profit(date):
    """Calculate total profit for a specific date from BigQuery"""
    try:
        from utils.bigquery_database import BigQueryDatabase
        db = BigQueryDatabase()
        
        # Query BigQuery for trades on the specific date
        start_datetime = datetime.combine(date, datetime.min.time())
        end_datetime = datetime.combine(date, datetime.max.time())
        
        # Get trades from BigQuery for the date range
        filters = {
            'start_date': start_datetime,
            'end_date': end_datetime,
            'run_name': 'testBot'  # Only get test bot trades
        }
        
        trades = db.get_trades(filters=filters, limit=None)
        
        # Calculate total profit for the day
        total_profit = sum(trade.get('profit', 0.0) for trade in trades)
        
        if VERBOSE_STREAK_LOGGING and trades:
            logger.info(f"Found {len(trades)} trades on {date}, total profit: ${total_profit:.2f}")
        
        return total_profit
        
    except Exception as e:
        logger.warning(f"Failed to get daily profit from BigQuery for {date}: {e}")
        # Fallback to local calculation if BigQuery fails
        return calculate_daily_profit_local(date)

def calculate_daily_profit_local(date):
    """Fallback: Calculate total profit for a specific date from local data"""
    total_profit = 0.0
    
    for symbol, strategies in trade_history.items():
        for strategy_name, data in strategies.items():
            if isinstance(data, dict) and 'trades' in data:
                for trade in data['trades']:
                    if 'timestamp' in trade:
                        try:
                            trade_date = datetime.strptime(trade['timestamp'], "%Y-%m-%d %H:%M:%S").date()
                            if trade_date == date:
                                # Calculate profit for completed trades
                                if trade['type'] == 'SELL':
                                    # Find corresponding BUY trade
                                    buy_trade = None
                                    for prev_trade in data['trades']:
                                        if (prev_trade['type'] == 'BUY' and 
                                            prev_trade['timestamp'] < trade['timestamp']):
                                            buy_trade = prev_trade
                                            break
                                    
                                    if buy_trade:
                                        profit = (trade['price'] - buy_trade['price']) * trade['quantity']
                                        total_profit += profit
                        except (ValueError, KeyError):
                            continue
    
    return total_profit

def display_automation_status():
    """Display current automation status"""
    bot_core.display_performance_summary()

def run_bot(interval=900):  # Default to 15 minutes (900 seconds)
    """Main bot loop"""
    try:
        # Load existing trade history at startup
        global trade_history
        trade_history = load_trade_history()
        
        # Display current performance
        display_performance_summary()
        display_strategy_performance()
        display_pair_performance()
        display_automation_status()
        
        # Initialize cycle counter
        cycle_count = 0
        
        while True:
            cycle_count += 1
            current_time = datetime.now()
            
            # Check streak conditions
            trading_enabled = check_streak_conditions()
            
            logger.info(f"=== CYCLE {cycle_count} - {current_time.strftime('%Y-%m-%d %H:%M:%S')} ===")
            logger.info(f"Trading Status: {'🟢 ENABLED' if trading_enabled else '🔴 DISABLED'}")
            logger.info(f"Next cycle in {interval/60:.1f} minutes")
            
            # Only execute trades if enabled
            if trading_enabled:
                all_data, all_signals = analyze_market()
                if all_data and all_signals:
                    try:
                        execute_trades(all_signals, all_data)
                        
                        # Display updated performance after trades
                        display_performance_summary()
                        display_strategy_performance()
                        display_pair_performance()
                    except Exception as e:
                        logger.error(f"Error executing trades: {e}")
                        # Provide more detailed error information
                        import traceback
                        logger.error(f"Error details: {traceback.format_exc()}")
                        # Continue running even if there's an error with one trade
            else:
                # Still analyze market but don't execute trades
                all_data, all_signals = analyze_market()
                if all_data and all_signals:
                    logger.info("Trading disabled - analyzing market only")
            
            # Save trade history periodically
            save_trade_history()
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        # Save final state and display final performance
        save_trade_history()
        display_performance_summary()
        display_strategy_performance()
        display_pair_performance()
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        # Save state on error
        save_trade_history()

def debug_trade_history():
    """Debug function to print out trade history structure"""
    print("\n--- DEBUG: Trade History Structure ---")
    for symbol, strategies in trade_history.items():
        print(f"Symbol: {symbol}")
        if not isinstance(strategies, dict):
            print(f"  WARNING: Expected dictionary for strategies, got {type(strategies)}")
            continue
            
        for strategy_name, data in strategies.items():
            print(f"  Strategy: {strategy_name}")
            if isinstance(data, dict):
                print(f"    Profit: {data.get('profit_usd', 'N/A')}")
                trades = data.get('trades', [])
                print(f"    Trades: {len(trades)}")
                if trades and len(trades) > 0:
                    print(f"    First trade: {trades[0]}")
            else:
                print(f"    WARNING: Expected dictionary for data, got {type(data)}")
    print("--- END DEBUG ---\n")

# Call this at startup
if __name__ == "__main__":
    # Display current prices
    print("Current Crypto Prices:")
    for coin, symbol in symbols.items():
        try:
            price = client.get_symbol_ticker(symbol=symbol)
            print(f"{coin}: ${float(price['price']):.2f}")
        except Exception as e:
            print(f"Error getting price for {coin}: {e}")
    
    # Load trade history before starting
    trade_history = load_trade_history()
    debug_trade_history()
    
    # Start the bot with 15-minute intervals
    logger.info("🚀 Starting TestBot with 15-minute intervals...")
    run_bot(interval=900)  # 15 minutes = 900 seconds
