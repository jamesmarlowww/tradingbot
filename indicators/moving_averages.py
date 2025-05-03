import pandas as pd

def calculate_moving_averages(client, symbol, interval, limit=100):
    """Calculate multiple moving averages across different timeframes"""
    ma_data = {}
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    closing_prices = [float(kline[4]) for kline in klines]
    prices_df = pd.DataFrame(closing_prices, columns=['close'])
    
    # Calculate different MA lengths
    prices_df['MA7'] = prices_df['close'].rolling(7).mean()
    prices_df['MA25'] = prices_df['close'].rolling(25).mean()
    prices_df['MA99'] = prices_df['close'].rolling(99).mean()
    
    # Exponential moving averages
    prices_df['EMA12'] = prices_df['close'].ewm(span=12).mean()
    prices_df['EMA26'] = prices_df['close'].ewm(span=26).mean()
    
    ma_data[interval] = prices_df.iloc[-1].to_dict()  # Get most recent values
    
    return ma_data