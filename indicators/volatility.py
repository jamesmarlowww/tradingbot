import pandas as pd

def calculate_bollinger_bands(close_prices, window=20, num_std=2):
    """Calculate Bollinger Bands"""
    middle_band = close_prices.rolling(window=window).mean()
    std_dev = close_prices.rolling(window=window).std()
    upper_band = middle_band + (std_dev * num_std)
    lower_band = middle_band - (std_dev * num_std)
    return upper_band, middle_band, lower_band

def calculate_atr(high, low, close, window=14):
    """Calculate Average True Range"""
    high_low = high - low
    high_close = (high - close.shift()).abs()
    low_close = (low - close.shift()).abs()
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    
    return true_range.rolling(window).mean()