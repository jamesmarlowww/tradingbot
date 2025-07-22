import os
import sys

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from binance.client import Client
import pandas as pd
import time
from config.config import API_KEY, API_SECRET, TESTNET, TESTNET_API_URL
from trading.strategies import MovingAverageCrossover, RSIStrategy, BollingerBandStrategy, RelativeStrengthStrategy, EnhancedRSIStrategy, RSIDivergenceStrategy, TrendFollowingStrategy
import logging
from datetime import datetime

from utils.indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands, calculate_atr
from utils.backtest_utils import prepare_data, calculate_position_size, calculate_fee_adjusted_profit, check_stop_loss_take_profit
from utils.performance_utils import generate_performance_report, save_trade_history, load_trade_history
from utils.trade_utils import execute_trade, update_open_positions, backup_trade_history, restore_from_backup

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

# Initialize Binance client
client = Client(API_KEY, API_SECRET, testnet=TESTNET)
if TESTNET:
    client.API_URL = TESTNET_API_URL

# ===== PRODUCTION TRADING CONFIGURATION =====
# Define all production trading combinations
# Format: (symbol, strategy_name, timeframe)
PROD_TRADING_COMBOS = [
    # ETHUSDT combinations
    ("ETHUSDT", "EnhancedRSIStrategy", "4h"),
    
    # SOLUSDT combinations
    ("SOLUSDT", "TrendFollowingStrategy", "1h"),
    
    # LINKUSDT combinations
    ("LINKUSDT", "EnhancedRSIStrategy", "4h")
]

# Extract unique symbols and timeframes
symbols = {combo[0]: combo[0] for combo in PROD_TRADING_COMBOS}
timeframes = {combo[2] for combo in PROD_TRADING_COMBOS}

# Print active configuration
logger.info("\n=== PRODUCTION TRADING CONFIGURATION ===")
for symbol, strategy, timeframe in PROD_TRADING_COMBOS:
    logger.info(f"Symbol: {symbol}, Strategy: {strategy}, Timeframe: {timeframe}")
logger.info("===================================\n")

# Risk management parameters
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
        
        # Second pass: Generate signals
        for coin, symbol in symbols.items():
            df = all_data[symbol]
            symbol_signals = {}
            
            # Generate signals from active strategies
            for strategy_name in active_strategies[symbol]:
                try:
                    strategy = strategies[symbol][strategy_name]
                    logger.info(f"Generating signals for {symbol} using {strategy_name}")
                    
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
        timestamp = datetime.now()
        
        # Check for stop loss and take profit on existing positions
        closed_positions = update_open_positions(
            trade_history[symbol]['open_positions'],
            current_price,
            timestamp,
            stop_loss_pct,
            take_profit_pct
        )
        
        # Update trade history with closed positions
        for position in closed_positions:
            strategy = position['strategy']
            trade_history[symbol][strategy]['trades'].append(position)
            trade_history[symbol][strategy]['profit_usd'] += position['profit']
        
        # Generate new trades based on signals
        for strategy_name in active_strategies[symbol]:
            signals = all_signals[symbol][strategy_name]
            if signals is None or signals.empty:
                continue
            
            latest_signal = signals.iloc[-1]
            if latest_signal['position'] != 0:  # We have a signal
                # Calculate position size
                position_size = calculate_position_size(
                    current_price,
                    symbol,
                    available_balance,
                    max_position_size
                )
                
                # Execute trade
                trade = execute_trade(
                    symbol,
                    'LONG' if latest_signal['position'] > 0 else 'SHORT',
                    current_price,
                    timestamp,
                    strategy_name,
                    position_size,
                    stop_loss_pct,
                    take_profit_pct
                )
                
                # Add to open positions
                trade_history[symbol]['open_positions'].append(trade)
                logger.info(f"New {trade['type']} position opened for {symbol} using {strategy_name}")

def run_bot(interval=60):
    """Main bot loop"""
    logger.info("Starting production trading bot...")
    
    while True:
        try:
            # Analyze market and get signals
            all_data, all_signals = analyze_market()
            
            # Execute trades based on signals
            execute_trades(all_signals, all_data)
            
            # Save trade history
            save_trade_history(trade_history, 'data/history/trade_history.json')
            
            # Backup trade history
            backup_trade_history('data/history/trade_history.json')
            
            # Sleep for the specified interval
            time.sleep(interval)
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            time.sleep(interval)

if __name__ == "__main__":
    run_bot() 