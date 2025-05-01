import numpy as np
import pandas as pd
import logging

class MovingAverageCrossover:
    """Simple Moving Average Crossover Strategy"""
    
    def __init__(self, short_window=12, long_window=26):
        self.short_window = short_window
        self.long_window = long_window
        self.position = 0  # 1 = long, 0 = neutral, -1 = short
    
    def generate_signals(self, df):
        """Generate buy/sell signals based on MA crossover"""
        signals = pd.DataFrame(index=df.index)
        signals['price'] = df['close']
        
        # Calculate moving averages
        signals['short_ma'] = df['close'].rolling(window=self.short_window).mean()
        signals['long_ma'] = df['close'].rolling(window=self.long_window).mean()
        
        # Initialize signal column
        signals['signal'] = 0.0
        
        # Generate signals only after both MAs are available
        valid_period = max(self.short_window, self.long_window)
        
        # Use iloc for positional indexing
        signals.iloc[valid_period:, signals.columns.get_loc('signal')] = np.where(
            signals['short_ma'].iloc[valid_period:] > signals['long_ma'].iloc[valid_period:], 1.0, 0.0
        )
        
        # Generate trading orders
        signals['position'] = signals['signal'].diff()
        
        return signals

class RSIStrategy:
    """RSI Mean-Reversion Strategy"""
    
    def __init__(self, rsi_period=14, overbought=70, oversold=30):
        self.rsi_period = rsi_period
        self.overbought = overbought
        self.oversold = oversold
        self.position = 0
        
    def generate_signals(self, df):
        signals = pd.DataFrame(index=df.index)
        signals['price'] = df['close']
        signals['rsi'] = df['rsi']
        signals['signal'] = 0.0
        
        # Buy signal when RSI crosses below oversold
        signals.loc[signals['rsi'] < self.oversold, 'signal'] = 1.0
        
        # Sell signal when RSI crosses above overbought
        signals.loc[signals['rsi'] > self.overbought, 'signal'] = -1.0
        
        # Calculate position changes
        signals['position'] = signals['signal'].diff()
        
        return signals

class EnhancedRSIStrategy:
    """Enhanced RSI strategy with dynamic thresholds and trend confirmation"""
    
    def __init__(self, rsi_period=14, oversold_threshold=30, overbought_threshold=70, 
                 trend_period=20, volatility_period=20, volatility_factor=0.5):
        self.rsi_period = rsi_period
        self.base_oversold = oversold_threshold
        self.base_overbought = overbought_threshold
        self.trend_period = trend_period
        self.volatility_period = volatility_period
        self.volatility_factor = volatility_factor
        self.logger = logging.getLogger(__name__)
    
    def generate_signals(self, df):
        try:
            if len(df) == 0:
                return pd.DataFrame()
                
            # Calculate RSI
            rsi = df['rsi']
            
            # Calculate trend
            df['sma'] = df['close'].rolling(window=self.trend_period).mean()
            trend = (df['close'] > df['sma']).astype(int) - (df['close'] < df['sma']).astype(int)
            
            # Calculate volatility
            df['returns'] = df['close'].pct_change()
            volatility = df['returns'].rolling(window=self.volatility_period).std()
            
            # Adjust thresholds based on volatility
            volatility_adjustment = volatility * self.volatility_factor
            oversold = self.base_oversold - volatility_adjustment
            overbought = self.base_overbought + volatility_adjustment
            
            # Generate signals
            signals = pd.DataFrame(index=df.index)
            signals['rsi'] = rsi
            signals['position'] = 0
            signals['signal'] = 0
            signals['oversold_threshold'] = oversold
            signals['overbought_threshold'] = overbought
            
            if len(signals) > 0:
                # Log current state
                self.logger.info(f"EnhancedRSI - Current state: RSI={rsi.iloc[-1]:.2f}, Oversold={oversold.iloc[-1]:.2f}, Overbought={overbought.iloc[-1]:.2f}")
                self.logger.info(f"EnhancedRSI - Current trend: {trend.iloc[-1]}")
                self.logger.info(f"EnhancedRSI - Current volatility: {volatility.iloc[-1]:.4f}")
            
            # Buy signal: RSI below oversold and uptrend
            buy_condition = (rsi < oversold) & (trend > 0)
            signals.loc[buy_condition, 'position'] = 1
            signals.loc[buy_condition, 'signal'] = 1
            
            # Sell signal: RSI above overbought and downtrend
            sell_condition = (rsi > overbought) & (trend < 0)
            signals.loc[sell_condition, 'position'] = -1
            signals.loc[sell_condition, 'signal'] = -1
            
            # Log signal generation
            if buy_condition.any():
                buy_indices = buy_condition[buy_condition].index
                self.logger.info(f"EnhancedRSI - Buy signals generated at: {buy_indices}")
            
            if sell_condition.any():
                sell_indices = sell_condition[sell_condition].index
                self.logger.info(f"EnhancedRSI - Sell signals generated at: {sell_indices}")
            
            if len(signals) > 0:
                # Log latest signal
                latest_signal = signals['signal'].iloc[-1]
                if latest_signal != 0:
                    self.logger.info(f"EnhancedRSI - Latest signal: {latest_signal}")
                else:
                    self.logger.info("EnhancedRSI - No signals generated")
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in EnhancedRSIStrategy: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return pd.DataFrame()

class BollingerBandStrategy:
    """Bollinger Bands Breakout/Reversion Strategy"""
    
    def __init__(self, strategy_type='breakout'):
        self.strategy_type = strategy_type  # 'breakout' or 'reversion'
        self.position = 0
        
    def generate_signals(self, df):
        signals = pd.DataFrame(index=df.index)
        signals['price'] = df['close']
        signals['upper_band'] = df['upper_band']
        signals['middle_band'] = df['middle_band']
        signals['lower_band'] = df['lower_band']
        signals['signal'] = 0.0
        
        if self.strategy_type == 'breakout':
            # Breakout strategy
            # Buy when price breaks above upper band
            signals.loc[signals['price'] > signals['upper_band'], 'signal'] = 1.0
            
            # Sell when price breaks below lower band
            signals.loc[signals['price'] < signals['lower_band'], 'signal'] = -1.0
            
        else:
            # Mean reversion strategy
            # Buy when price touches lower band (oversold)
            signals.loc[signals['price'] < signals['lower_band'], 'signal'] = 1.0
            
            # Sell when price touches upper band (overbought)
            signals.loc[signals['price'] > signals['upper_band'], 'signal'] = -1.0
        
        # Calculate position changes
        signals['position'] = signals['signal'].diff()
        
        return signals

class RelativeStrengthStrategy:
    """Strategy that trades based on relative performance between assets"""
    
    def __init__(self, lookback_period=24, threshold=5.0):
        self.lookback_period = lookback_period  # Hours to look back
        self.threshold = threshold  # Percentage threshold to trigger trades
        self.position = 0
    
    def generate_signals(self, df, comparison_dfs=None):
        """
        Generate signals based on relative performance
        df: DataFrame for the primary asset
        comparison_dfs: Dictionary of DataFrames for comparison assets
        """
        if comparison_dfs is None or len(comparison_dfs) == 0:
            return pd.DataFrame()  # Need comparison assets
            
        signals = pd.DataFrame(index=df.index)
        signals['price'] = df['close']
        signals['signal'] = 0.0
        
        # Calculate percentage change over lookback period
        lookback_rows = min(self.lookback_period * 60, len(df) - 1)  # Convert hours to minutes
        primary_change = (df['close'].iloc[-1] / df['close'].iloc[-lookback_rows] - 1) * 100
        
        # Compare with other assets
        comparisons = []
        for symbol, comp_df in comparison_dfs.items():
            if len(comp_df) < lookback_rows:
                continue
                
            comp_change = (comp_df['close'].iloc[-1] / comp_df['close'].iloc[-lookback_rows] - 1) * 100
            comparisons.append((symbol, comp_change))
            
            # Calculate relative strength
            relative_diff = primary_change - comp_change
            
            # If this asset underperformed significantly, buy (mean reversion)
            if relative_diff < -self.threshold:
                signals.loc[signals.index[-1], 'signal'] = 1.0
                
            # If this asset outperformed significantly, sell (mean reversion)
            elif relative_diff > self.threshold:
                signals.loc[signals.index[-1], 'signal'] = -1.0
        
        # Calculate position changes
        signals['position'] = signals['signal'].diff()
        
        # Store comparison data for logging
        signals['primary_change'] = primary_change
        signals['comparisons'] = str(comparisons)
        
        return signals

class RSIDivergenceStrategy:
    """Strategy that looks for divergences between price and RSI"""
    
    def __init__(self, rsi_period=14, divergence_threshold=0.1):
        self.rsi_period = rsi_period
        self.divergence_threshold = divergence_threshold
        self.logger = logging.getLogger(__name__)
    
    def _find_local_minima(self, series, window=5):
        """Find local minima in a time series"""
        local_minima = []
        for i in range(window, len(series) - window):
            if all(series.iloc[i] <= series.iloc[i-j] for j in range(1, window+1)) and \
               all(series.iloc[i] <= series.iloc[i+j] for j in range(1, window+1)):
                local_minima.append(series.iloc[i])
            else:
                local_minima.append(None)
        return pd.Series(local_minima, index=series.index[window:-window])
    
    def _find_local_maxima(self, series, window=5):
        """Find local maxima in a time series"""
        local_maxima = []
        for i in range(window, len(series) - window):
            if all(series.iloc[i] >= series.iloc[i-j] for j in range(1, window+1)) and \
               all(series.iloc[i] >= series.iloc[i+j] for j in range(1, window+1)):
                local_maxima.append(series.iloc[i])
            else:
                local_maxima.append(None)
        return pd.Series(local_maxima, index=series.index[window:-window])
        
    def generate_signals(self, df):
        try:
            if len(df) == 0:
                return pd.DataFrame()
                
            signals = pd.DataFrame(index=df.index)
            signals['price'] = df['close']
            signals['rsi'] = df['rsi']
            signals['signal'] = 0
            
            # Find local extrema
            price_minima = self._find_local_minima(df['close'])
            price_maxima = self._find_local_maxima(df['close'])
            rsi_minima = self._find_local_minima(df['rsi'])
            rsi_maxima = self._find_local_maxima(df['rsi'])
            
            self.logger.info(f"RSIDivergence - Found {len(price_minima.dropna())} price minima, {len(price_maxima.dropna())} price maxima")
            self.logger.info(f"RSIDivergence - Found {len(rsi_minima.dropna())} RSI minima, {len(rsi_maxima.dropna())} RSI maxima")
            
            # Process bullish divergence (price making lower lows but RSI making higher lows)
            self.logger.info("RSIDivergence - Processing price minima and RSI minima")
            for i in range(len(price_minima)-1):
                if pd.isna(price_minima.iloc[i]) or pd.isna(price_minima.iloc[i+1]):
                    continue
                if pd.isna(rsi_minima.iloc[i]) or pd.isna(rsi_minima.iloc[i+1]):
                    continue
                    
                if price_minima.iloc[i+1] < price_minima.iloc[i] and rsi_minima.iloc[i+1] > rsi_minima.iloc[i]:
                    signals.loc[price_minima.index[i+1], 'signal'] = 1  # Bullish signal
            
            # Process bearish divergence (price making higher highs but RSI making lower highs)
            self.logger.info("RSIDivergence - Processing price maxima and RSI maxima")
            for i in range(len(price_maxima)-1):
                if pd.isna(price_maxima.iloc[i]) or pd.isna(price_maxima.iloc[i+1]):
                    continue
                if pd.isna(rsi_maxima.iloc[i]) or pd.isna(rsi_maxima.iloc[i+1]):
                    continue
                    
                if price_maxima.iloc[i+1] > price_maxima.iloc[i] and rsi_maxima.iloc[i+1] < rsi_maxima.iloc[i]:
                    signals.loc[price_maxima.index[i+1], 'signal'] = -1  # Bearish signal
            
            # Calculate position changes
            signals['position'] = signals['signal'].diff()
            
            if len(signals) > 0:
                latest_signal = signals['signal'].iloc[-1]
                if latest_signal != 0:
                    self.logger.info(f"RSIDivergence - Latest signal: {latest_signal}")
                else:
                    self.logger.info("RSIDivergence - No signals generated")
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in RSIDivergenceStrategy: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return pd.DataFrame()

class MomentumStrategy:
    """Simple momentum strategy based on price changes"""
    
    def __init__(self, period=3, threshold=0.001):
        self.period = period
        self.threshold = threshold
        self.logger = logging.getLogger(__name__)
    
    def generate_signals(self, df):
        try:
            if len(df) == 0:
                return pd.DataFrame()
                
            signals = pd.DataFrame(index=df.index)
            signals['price'] = df['close']
            
            # Calculate price change over period
            price_change = df['close'].pct_change(periods=self.period)
            
            # Generate signals
            signals['signal'] = 0
            signals.loc[price_change > self.threshold, 'signal'] = 1  # Buy on upward momentum
            signals.loc[price_change < -self.threshold, 'signal'] = -1  # Sell on downward momentum
            
            # Calculate position changes
            signals['position'] = signals['signal'].diff()
            
            if len(signals) > 0:
                latest_signal = signals['signal'].iloc[-1]
                if latest_signal != 0:
                    self.logger.info(f"Momentum - Latest signal: {latest_signal}")
                else:
                    self.logger.info("Momentum - No signals generated")
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in MomentumStrategy: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return pd.DataFrame()

class TrendFollowingStrategy:
    """Simple trend following strategy"""
    
    def __init__(self, period=3, threshold=0.001):
        self.period = period
        self.threshold = threshold
        self.logger = logging.getLogger(__name__)
    
    def generate_signals(self, df):
        try:
            if len(df) == 0:
                return pd.DataFrame()
                
            signals = pd.DataFrame(index=df.index)
            signals['price'] = df['close']
            
            # Calculate moving average
            ma = df['close'].rolling(window=self.period).mean()
            
            # Calculate price deviation from MA
            deviation = (df['close'] - ma) / ma
            
            # Generate signals
            signals['signal'] = 0
            signals.loc[deviation > self.threshold, 'signal'] = 1  # Buy when price above MA
            signals.loc[deviation < -self.threshold, 'signal'] = -1  # Sell when price below MA
            
            # Calculate position changes
            signals['position'] = signals['signal'].diff()
            
            if len(signals) > 0:
                latest_signal = signals['signal'].iloc[-1]
                if latest_signal != 0:
                    self.logger.info(f"TrendFollowing - Latest signal: {latest_signal}")
                else:
                    self.logger.info("TrendFollowing - No signals generated")
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in TrendFollowingStrategy: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return pd.DataFrame()