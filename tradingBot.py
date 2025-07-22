import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pandas_ta as ta

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

from binance.client import Client
from config.config import API_KEY, API_SECRET, TESTNET, TESTNET_API_URL

class TradingBot:
    def __init__(self):
        self.client = Client(API_KEY, API_SECRET, testnet=TESTNET)
        if TESTNET:
            self.client.API_URL = TESTNET_API_URL
        
    def get_historical_data(self, symbol='BTCUSDT', interval='1h', lookback='7 days ago UTC'):
        """Fetch historical klines/candlestick data"""
        klines = self.client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            start_str=lookback
        )
        
        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Convert string values to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
            
        return df
    
    def calculate_indicators(self, df):
        """Calculate technical indicators"""
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # MACD
        macd = ta.macd(df['close'])
        df = pd.concat([df, macd], axis=1)
        
        # Moving Averages
        df['sma_20'] = ta.sma(df['close'], length=20)
        df['sma_50'] = ta.sma(df['close'], length=50)
        
        return df
    
    def generate_signals(self, df):
        """Generate trading signals based on technical indicators"""
        signals = pd.DataFrame(index=df.index)
        
        # RSI signals
        signals['rsi_signal'] = 0
        signals.loc[df['rsi'] < 30, 'rsi_signal'] = 1  # Oversold
        signals.loc[df['rsi'] > 70, 'rsi_signal'] = -1  # Overbought
        
        # MACD signals
        signals['macd_signal'] = 0
        signals.loc[df['MACD_12_26_9'] > df['MACDs_12_26_9'], 'macd_signal'] = 1
        signals.loc[df['MACD_12_26_9'] < df['MACDs_12_26_9'], 'macd_signal'] = -1
        
        # Moving Average signals
        signals['ma_signal'] = 0
        signals.loc[df['sma_20'] > df['sma_50'], 'ma_signal'] = 1
        signals.loc[df['sma_20'] < df['sma_50'], 'ma_signal'] = -1
        
        # Combined signal
        signals['combined_signal'] = signals['rsi_signal'] + signals['macd_signal'] + signals['ma_signal']
        
        return signals
    
    def run_analysis(self, symbol='BTCUSDT', interval='1h'):
        """Run the complete analysis"""
        # Get historical data
        df = self.get_historical_data(symbol=symbol, interval=interval)
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        # Generate signals
        signals = self.generate_signals(df)
        
        # Get the latest signal
        latest_signal = signals['combined_signal'].iloc[-1]
        
        return {
            'data': df,
            'signals': signals,
            'latest_signal': latest_signal,
            'current_price': df['close'].iloc[-1],
            'timestamp': df['timestamp'].iloc[-1]
        }

if __name__ == "__main__":
    bot = TradingBot()
    analysis = bot.run_analysis()
    
    print(f"Current BTC Price: ${analysis['current_price']:.2f}")
    print(f"Latest Signal: {analysis['latest_signal']}")
    print(f"Timestamp: {analysis['timestamp']}") 