import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from utils.indicators import calculate_rsi, calculate_ema, calculate_macd, calculate_bollinger_bands, calculate_atr

logger = logging.getLogger(__name__)

def prepare_data(df):
    """Prepare data for backtesting by calculating all necessary indicators"""
    # Check if timestamp is already the index and converted to datetime
    if df.index.name == 'timestamp' and pd.api.types.is_datetime64_any_dtype(df.index):
        # Timestamp is already the index and converted, no need to process it
        pass
    else:
        # Convert timestamp to datetime if it's still a column
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Calculate technical indicators
    df['rsi'] = calculate_rsi(df['close'])
    df['macd'], df['signal'], df['histogram'] = calculate_macd(df['close'])
    df['upper_band'], df['middle_band'], df['lower_band'] = calculate_bollinger_bands(df['close'])
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
    
    # Calculate moving averages
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['sma_200'] = df['close'].rolling(window=200).mean()
    
    # Calculate price changes
    df['price_change'] = df['close'].pct_change()
    df['volume_change'] = df['volume'].pct_change()
    
    return df

def calculate_position_size(price, symbol, balance, max_position_size=0.05):
    """Calculate position size based on current balance and risk parameters"""
    position_value = balance * max_position_size
    return position_value / price

def calculate_fee_adjusted_profit(trade, fee_rate=0.001):
    """Calculate profit/loss including trading fees"""
    entry_price = trade['entry_price']
    exit_price = trade['exit_price']
    position_size = trade['position_size']
    trade_type = trade['type']
    
    # Calculate gross profit/loss
    if trade_type == 'LONG':
        gross_profit = (exit_price - entry_price) * position_size
    else:  # SHORT
        gross_profit = (entry_price - exit_price) * position_size
    
    # Calculate fees
    entry_fee = entry_price * position_size * fee_rate
    exit_fee = exit_price * position_size * fee_rate
    total_fees = entry_fee + exit_fee
    
    # Calculate net profit/loss
    net_profit = gross_profit - total_fees
    
    return net_profit, total_fees

def check_stop_loss_take_profit(position, current_price, stop_loss_pct=0.015, take_profit_pct=0.045):
    """Check if stop loss or take profit has been hit - optimized for better risk/reward"""
    entry_price = position['entry_price']
    trade_type = position['type']
    
    if trade_type == 'LONG':
        stop_loss = entry_price * (1 - stop_loss_pct)
        take_profit = entry_price * (1 + take_profit_pct)
        return current_price <= stop_loss, current_price >= take_profit
    else:  # SHORT
        stop_loss = entry_price * (1 + stop_loss_pct)
        take_profit = entry_price * (1 - take_profit_pct)
        return current_price >= stop_loss, current_price <= take_profit

def should_close_trade_for_minimum_profit(position, current_price, min_profit_pct=0.005):
    """Check if trade should be closed for minimum profit (to avoid fee erosion)"""
    entry_price = position['entry_price']
    trade_type = position['type']
    
    if trade_type == 'LONG':
        profit_pct = (current_price - entry_price) / entry_price
        return profit_pct >= min_profit_pct
    else:  # SHORT
        profit_pct = (entry_price - current_price) / entry_price
        return profit_pct >= min_profit_pct 