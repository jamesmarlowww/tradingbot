import pandas as pd

def calculate_price_features(client, symbol, interval):
    """Calculate price action features"""
    klines = client.get_klines(symbol=symbol, interval=interval, limit=100)
    
    # Create DataFrame
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                      'quote_asset_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignored'])
    
    # Convert data types
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col])
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Price movement features
    df['return'] = df['close'].pct_change() * 100
    df['range'] = df['high'] - df['low']
    df['body_size'] = abs(df['close'] - df['open'])
    df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
    
    # Support and resistance
    df['support_level'] = df['low'].rolling(20).min()
    df['resistance_level'] = df['high'].rolling(20).max()
    
    return df