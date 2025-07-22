import os
import sys

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from binance.client import Client
import pandas as pd
import time
from config.config import API_KEY, API_SECRET, TESTNET, TESTNET_API_URL
from indicators.moving_averages import calculate_moving_averages
from indicators.momentum import calculate_rsi, calculate_macd
from indicators.volatility import calculate_bollinger_bands, calculate_atr
from indicators.price_action import calculate_price_features
from trading.execution import TradeExecutor
from trading.strategies import MovingAverageCrossover, RSIStrategy, BollingerBandStrategy, RelativeStrengthStrategy, EnhancedRSIStrategy, RSIDivergenceStrategy, TrendFollowingStrategy
import logging
import json
from datetime import datetime
import shutil
import glob

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

# Keep using Testnet
client = Client(API_KEY, API_SECRET, testnet=TESTNET)
if TESTNET:
    client.API_URL = TESTNET_API_URL

# ===== ACTIVE TRADING CONFIGURATION =====
# Define all active trading combinations
# Format: (symbol, strategy_name, timeframe)
ACTIVE_TRADING_COMBOS = [
    # ETHUSDT combinations
    ("ETHUSDT", "EnhancedRSIStrategy", "4h"),
    
    # SOLUSDT combinations
    ("SOLUSDT", "TrendFollowingStrategy", "1h"),
    
    # LINKUSDT combinations
    ("LINKUSDT", "EnhancedRSIStrategy", "4h")
]

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

# Initialize trade history
trade_history = {}
for symbol in symbols.values():
    trade_history[symbol] = {
        'EnhancedRSIStrategy': {'trades': [], 'profit_usd': 0.0},
        'TrendFollowingStrategy': {'trades': [], 'profit_usd': 0.0}
    }

# Initialize strategies for each symbol
strategies = {}
for symbol in symbols.values():
    strategies[symbol] = {
        'EnhancedRSIStrategy': EnhancedRSIStrategy(rsi_period=3, oversold_threshold=45, overbought_threshold=55, volatility_factor=0.01, trend_period=3),
        'TrendFollowingStrategy': TrendFollowingStrategy(period=3, threshold=0.001)
    }

# Choose which strategies to use for each symbol
active_strategies = {
    "ETHUSDT": ['EnhancedRSIStrategy'],  # 4h timeframe
    "SOLUSDT": ['TrendFollowingStrategy'],  # 1h timeframe
    "LINKUSDT": ['EnhancedRSIStrategy']     # 4h timeframe
}

# Create trade executors for each symbol
trade_executors = {
    symbol: TradeExecutor(client, symbol, test_mode=False)
    for symbol in symbols.values()
}

def analyze_market():
    """Gather market data and calculate indicators for all symbols"""
    try:
        all_data = {}
        all_signals = {}
        
        # First pass: Get data for all symbols
        for coin, symbol in symbols.items():
            logger.info(f"\n=== Data Update for {coin} ({symbol}) ===")
            
            # Set appropriate timeframe for each pair
            if symbol == "SOLUSDT":
                interval = Client.KLINE_INTERVAL_1HOUR
                timeframe = "1-hour"
            else:  # ETHUSDT and LINKUSDT
                interval = Client.KLINE_INTERVAL_4HOUR
                timeframe = "4-hour"
            
            logger.info(f"Fetching {timeframe} candles for {symbol}")
            
            # Get klines data with appropriate timeframe
            klines = client.get_klines(symbol=symbol, interval=interval, limit=100)
            
            # Create dataframe
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                            'quote_asset_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignored'])
            
            # Convert types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            # Calculate indicators
            logger.info(f"Calculating indicators for {symbol} using {timeframe} timeframe")
            df['rsi'] = calculate_rsi(df['close'])
            df['macd'], df['signal'], df['histogram'] = calculate_macd(df['close'])
            df['upper_band'], df['middle_band'], df['lower_band'] = calculate_bollinger_bands(df['close'])
            df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
            
            all_data[symbol] = df
            logger.info(f"Data update complete for {symbol}")
        
        # Second pass: Generate signals with comparisons for RelativeStrengthStrategy
        for coin, symbol in symbols.items():
            df = all_data[symbol]
            symbol_signals = {}
            
            # Generate signals from active strategies
            for strategy_name in active_strategies[symbol]:
                try:
                    strategy = strategies[symbol][strategy_name]
                    logger.info(f"Generating signals for {symbol} using {strategy_name}")
                    
                    if strategy_name == 'RelativeStrengthStrategy':
                        # Create comparison dataframes (excluding the current symbol)
                        comparison_dfs = {s: all_data[s] for s in all_data if s != symbol}
                        signals = strategy.generate_signals(df, comparison_dfs)
                    else:
                        signals = strategy.generate_signals(df)
                    
                    # Log signal information
                    if signals is not None and not signals.empty:
                        latest_signal = signals.iloc[-1]
                        signal_type = "BUY" if latest_signal['position'] > 0 else "SELL" if latest_signal['position'] < 0 else "NEUTRAL"
                        logger.info(f"{symbol} - {strategy_name} latest signal: {signal_type}")
                        
                        # For RSI strategies, log the RSI value
                        if 'rsi' in latest_signal:
                            logger.info(f"{symbol} - {strategy_name} RSI: {latest_signal['rsi']:.2f}")
                        
                        # For EnhancedRSIStrategy, log the thresholds
                        if strategy_name == 'EnhancedRSIStrategy' and 'oversold_threshold' in latest_signal:
                            logger.info(f"{symbol} - {strategy_name} thresholds: oversold={latest_signal['oversold_threshold']:.2f}, overbought={latest_signal.get('overbought_threshold', 'N/A')}")
                    else:
                        logger.info(f"{symbol} - {strategy_name} generated no signals")
                    
                    symbol_signals[strategy_name] = signals
                except Exception as e:
                    logger.error(f"Error generating signals for {symbol}/{strategy_name}: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    continue
            
            all_signals[symbol] = symbol_signals
        
        return all_data, all_signals
    except Exception as e:
        logger.error(f"Error analyzing market: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None, None

def execute_trades(all_signals, all_data):
    """Execute trades based on signals from multiple strategies across all symbols"""
    if all_signals is None:
        return
    
    for symbol in symbols.values():
        current_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        
        if symbol not in all_signals:
            continue
            
        symbol_signals = all_signals[symbol]
        
        for strategy_name, signals in symbol_signals.items():
            if signals is None or signals.empty:
                continue
            
            latest_signal = signals.iloc[-1]
            
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

def run_bot(interval=60):
    """Main bot loop"""
    try:
        # Load existing trade history at startup
        global trade_history
        trade_history = load_trade_history()
        
        # Display current performance
        display_performance_summary()
        display_strategy_performance()
        display_pair_performance()
        
        # Initialize loading indicator
        loading_chars = ["|", "/", "-", "\\"]
        loading_index = 0
        
        while True:
            # Show loading indicator
            print(f"\rBot running... {loading_chars[loading_index]} ", end="", flush=True)
            loading_index = (loading_index + 1) % len(loading_chars)
            
            # Your existing bot logic here
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
    
    # Start the bot
    run_bot(interval=60)  # Check market every 60 seconds
