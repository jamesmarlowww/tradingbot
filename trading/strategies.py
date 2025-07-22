import numpy as np
import pandas as pd
import logging

class MovingAverageCrossover:
    """Enhanced Moving Average Crossover Strategy with trend confirmation"""
    
    def __init__(self, short_window=8, long_window=21, volume_threshold=1.1, trend_period=50):
        self.short_window = short_window
        self.long_window = long_window
        self.volume_threshold = volume_threshold
        self.trend_period = trend_period
        self.logger = logging.getLogger(__name__)
        
        # Adjust parameters based on timeframe
        if hasattr(self, 'timeframe'):
            if self.timeframe == '4h':
                self.short_window = 12
                self.long_window = 30
                self.trend_period = 60
            elif self.timeframe == '1d':
                self.short_window = 16
                self.long_window = 40
                self.trend_period = 80
    
    def generate_signals(self, df):
        try:
            if len(df) == 0:
                return pd.DataFrame()
                
            signals = pd.DataFrame(index=df.index)
            signals['price'] = df['close']
            
            # Calculate moving averages
            signals['short_ma'] = df['close'].rolling(window=self.short_window, min_periods=1).mean()
            signals['long_ma'] = df['close'].rolling(window=self.long_window, min_periods=1).mean()
            
            # Calculate trend using multiple timeframes
            signals['sma_short'] = signals['price'].rolling(window=self.trend_period//2, min_periods=1).mean()
            signals['sma_long'] = signals['price'].rolling(window=self.trend_period, min_periods=1).mean()
            signals['trend_strength'] = (signals['sma_short'] - signals['sma_long']) / signals['sma_long']
            
            # Calculate volume metrics
            signals['volume_ma'] = df['volume'].rolling(window=self.short_window, min_periods=1).mean()
            signals['volume_ratio'] = df['volume'] / signals['volume_ma']
            signals['volume_trend'] = df['volume'].rolling(window=self.short_window, min_periods=1).mean() / \
                                    df['volume'].rolling(window=self.long_window, min_periods=1).mean()
            
            # Calculate volatility
            signals['returns'] = df['close'].pct_change()
            signals['volatility'] = signals['returns'].rolling(window=self.short_window, min_periods=1).std()
            signals['volatility_ma'] = signals['volatility'].rolling(window=self.long_window, min_periods=1).mean()
            
            # Calculate price momentum
            signals['momentum'] = signals['price'].pct_change(periods=self.short_window)
            signals['momentum_ma'] = signals['momentum'].rolling(window=self.short_window, min_periods=1).mean()
            
            # Initialize signal column
            signals['signal'] = 0.0
            
            # Generate signals with enhanced logic
            for idx in df.index:
                current_price = signals.loc[idx, 'price']
                current_short_ma = signals.loc[idx, 'short_ma']
                current_long_ma = signals.loc[idx, 'long_ma']
                current_trend = signals.loc[idx, 'trend_strength']
                current_volume_ratio = signals.loc[idx, 'volume_ratio']
                current_volume_trend = signals.loc[idx, 'volume_trend']
                current_volatility = signals.loc[idx, 'volatility']
                current_volatility_ma = signals.loc[idx, 'volatility_ma']
                current_momentum = signals.loc[idx, 'momentum']
                current_momentum_ma = signals.loc[idx, 'momentum_ma']
                
                # Skip if volatility is too high
                if current_volatility > current_volatility_ma * 1.5:  # Reduced from 1.8
                    continue
                
                # Skip if volume is too low
                if current_volume_ratio < 1.1 or current_volume_trend < 1.0:  # Reduced thresholds
                    continue
                
                # Generate signals with trend and momentum confirmation
                if (current_short_ma > current_long_ma and 
                    current_trend > 0.001 and  # Reduced from 0.002
                    current_volume_ratio > self.volume_threshold and 
                    current_volume_trend > 1.1 and  # Reduced from 1.2
                    current_momentum > current_momentum_ma):
                    signals.loc[idx, 'signal'] = 1.0
                elif (current_short_ma < current_long_ma and 
                      current_trend < -0.001 and  # Reduced from -0.002
                      current_volume_ratio > self.volume_threshold and 
                      current_volume_trend > 1.1 and  # Reduced from 1.2
                      current_momentum < current_momentum_ma):
                    signals.loc[idx, 'signal'] = -1.0
            
            # Calculate position changes
            signals['position'] = signals['signal'].diff()
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in MovingAverageCrossover: {e}")
            return pd.DataFrame()

class RSIStrategy:
    """Enhanced RSI Mean-Reversion Strategy with timeframe-specific parameters"""
    
    def __init__(self, timeframe='1h', rsi_period=None, overbought=None, oversold=None, trend_period=None):
        self.timeframe = timeframe
        
        # Set timeframe-specific parameters
        if timeframe == '1h':
            self.rsi_period = rsi_period or 14
            self.overbought = overbought or 70
            self.oversold = oversold or 30
            self.trend_period = trend_period or 20
        elif timeframe == '4h':
            self.rsi_period = rsi_period or 14
            self.overbought = overbought or 75
            self.oversold = oversold or 25
            self.trend_period = trend_period or 30
        elif timeframe == '1d':
            self.rsi_period = rsi_period or 14
            self.overbought = overbought or 80
            self.oversold = oversold or 20
            self.trend_period = trend_period or 50
        
        self.position = 0
        self.logger = logging.getLogger(__name__)
    
    def generate_signals(self, df):
        try:
            if len(df) == 0:
                return pd.DataFrame()
                
            signals = pd.DataFrame(index=df.index)
            signals['price'] = df['close']
            signals['rsi'] = df['rsi']
            
            # Calculate multiple moving averages for trend confirmation
            signals['sma_short'] = df['close'].rolling(window=self.trend_period//2, min_periods=1).mean()
            signals['sma_long'] = df['close'].rolling(window=self.trend_period, min_periods=1).mean()
            
            # Calculate trend strength
            signals['trend_strength'] = (signals['sma_short'] - signals['sma_long']) / signals['sma_long']
            
            # Calculate volatility
            signals['returns'] = df['close'].pct_change()
            volatility = signals['returns'].rolling(window=self.trend_period, min_periods=1).std()
            
            # Calculate volatility threshold
            volatility_threshold = volatility.rolling(window=20, min_periods=1).mean() * 1.5
            
            # Calculate volume metrics
            signals['volume_ma'] = df['volume'].rolling(window=self.trend_period, min_periods=1).mean()
            signals['volume_ratio'] = df['volume'] / signals['volume_ma']
            signals['volume_trend'] = df['volume'].rolling(window=self.trend_period//2, min_periods=1).mean() / \
                                    df['volume'].rolling(window=self.trend_period, min_periods=1).mean()
            
            # Initialize signal column
            signals['signal'] = 0.0
            
            # Generate signals with enhanced logic
            for idx in df.index:
                current_rsi = signals.loc[idx, 'rsi']
                current_trend_strength = signals.loc[idx, 'trend_strength']
                current_volatility = volatility.loc[idx]
                current_volume_ratio = signals.loc[idx, 'volume_ratio']
                current_volume_trend = signals.loc[idx, 'volume_trend']
                
                # Skip if volatility is too high
                if current_volatility > volatility_threshold.loc[idx]:
                    continue
                
                # Skip if volume is too low
                if current_volume_ratio < 1.2 or current_volume_trend < 1.1:
                    continue
                
                # Generate signals with trend confirmation
                if current_rsi < self.oversold and current_trend_strength > 0.002:
                    signals.loc[idx, 'signal'] = 1.0
                elif current_rsi > self.overbought and current_trend_strength < -0.002:
                    signals.loc[idx, 'signal'] = -1.0
            
            # Calculate position changes
            signals['position'] = signals['signal'].diff()
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in RSIStrategy: {e}")
            return pd.DataFrame()

class EnhancedRSIStrategy:
    """Enhanced RSI strategy with relaxed rules"""
    
    def __init__(self, rsi_period=14, oversold_threshold=45, overbought_threshold=55, 
                 trend_period=5, volatility_period=5, volatility_factor=0.1):
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
                
            signals = pd.DataFrame(index=df.index)
            signals['price'] = df['close']
            signals['rsi'] = df['rsi']
            
            # Calculate trend with shorter period
            signals['sma'] = df['close'].rolling(window=self.trend_period, min_periods=1).mean()
            trend = (df['close'] > signals['sma']).astype(int) - (df['close'] < signals['sma']).astype(int)
            
            # Calculate volatility with shorter period
            signals['returns'] = df['close'].pct_change()
            volatility = signals['returns'].rolling(window=self.volatility_period, min_periods=1).std()
            
            # Adjust thresholds based on volatility with reduced factor
            volatility_adjustment = volatility * self.volatility_factor
            oversold = self.base_oversold - volatility_adjustment
            overbought = self.base_overbought + volatility_adjustment
            
            # Initialize signal column
            signals['signal'] = 0.0
            
            # More aggressive signals
            signals.loc[signals['rsi'] < oversold, 'signal'] = 1.0
            signals.loc[signals['rsi'] > overbought, 'signal'] = -1.0
            
            # Calculate position changes
            signals['position'] = signals['signal'].diff()
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in EnhancedRSIStrategy: {e}")
            return pd.DataFrame()

class LiveReactiveRSIStrategy:
    """Strategy that uses RSI with dynamic thresholds based on market conditions"""
    
    def __init__(self, rsi_period=14, oversold_threshold=45, overbought_threshold=55, volatility_factor=0.02):
        self.rsi_period = rsi_period
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.volatility_factor = volatility_factor
        self.logger = logging.getLogger(__name__)
        
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on RSI, trend, and volatility.
        Uses RSI values already calculated in data preparation.
        """
        if data.empty:
            self.logger.warning("Empty DataFrame provided to LiveReactiveRSIStrategy")
            return pd.DataFrame()
            
        try:
            # Use RSI from prepared data
            rsi = data['rsi']
            self.logger.info(f"RSI range: {rsi.min():.2f} to {rsi.max():.2f}")
            
            # Calculate trend using shorter period for quicker response
            data['trend'] = data['close'].ewm(span=10, adjust=False).mean()
            
            # Calculate volatility using rolling standard deviation
            data['volatility'] = data['close'].pct_change().rolling(window=10).std()
            
            # Calculate mean volatility for comparison
            mean_volatility = data['volatility'].mean()
            self.logger.info(f"Mean volatility: {mean_volatility:.6f}")
            
            # Initialize signals
            signals = pd.DataFrame(index=data.index)
            signals['signal'] = 0
            signals['position'] = 0  # Add position column
            
            # Track signal generation
            buy_signals = 0
            sell_signals = 0
            skipped_volatility = 0
            
            # Generate signals based on RSI and volatility
            for i in range(1, len(data)):
                current_rsi = rsi.iloc[i]
                current_volatility = data['volatility'].iloc[i]
                
                # Log RSI and volatility values for debugging
                if i % 100 == 0:  # Log every 100th candle to avoid too much output
                    self.logger.info(f"Candle {i}: RSI={current_rsi:.2f}, Volatility={current_volatility:.6f} (Mean={mean_volatility:.6f})")
                
                # Skip if volatility is extremely high (5x mean)
                if current_volatility > 5 * mean_volatility:
                    skipped_volatility += 1
                    if i % 100 == 0:  # Log skipped trades periodically
                        self.logger.info(f"Skipped trade at candle {i} due to high volatility: {current_volatility:.6f} > {5 * mean_volatility:.6f}")
                    continue
                    
                # Generate buy signal when RSI is oversold
                if current_rsi < self.oversold_threshold:
                    signals.iloc[i, signals.columns.get_loc('signal')] = 1
                    signals.iloc[i, signals.columns.get_loc('position')] = 1  # Set position directly
                    buy_signals += 1
                    self.logger.info(f"Buy signal generated at {data.index[i]}: RSI={current_rsi:.2f}")
                    
                # Generate sell signal when RSI is overbought
                elif current_rsi > self.overbought_threshold:
                    signals.iloc[i, signals.columns.get_loc('signal')] = -1
                    signals.iloc[i, signals.columns.get_loc('position')] = -1  # Set position directly
                    sell_signals += 1
                    self.logger.info(f"Sell signal generated at {data.index[i]}: RSI={current_rsi:.2f}")
            
            # Log signal statistics
            self.logger.info(f"Generated {buy_signals} buy signals and {sell_signals} sell signals")
            self.logger.info(f"Skipped {skipped_volatility} trades due to high volatility")
            
            # Log if no signals were generated
            if buy_signals == 0 and sell_signals == 0:
                self.logger.warning("No signals were generated by LiveReactiveRSIStrategy")
                self.logger.warning(f"RSI thresholds: oversold={self.oversold_threshold}, overbought={self.overbought_threshold}")
                self.logger.warning(f"RSI range in data: {rsi.min():.2f} to {rsi.max():.2f}")
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in LiveReactiveRSIStrategy: {e}")
            return pd.DataFrame()

class BollingerBandStrategy:
    """Enhanced Bollinger Bands Strategy with trend confirmation"""
    
    def __init__(self, strategy_type='breakout', period=20, std_dev=2.0, trend_period=50):
        self.strategy_type = strategy_type
        self.period = period
        self.std_dev = std_dev
        self.trend_period = trend_period
        self.logger = logging.getLogger(__name__)
        
        # Adjust parameters based on timeframe
        if hasattr(self, 'timeframe'):
            if self.timeframe == '4h':
                self.period = 30
                self.std_dev = 2.2
                self.trend_period = 60
            elif self.timeframe == '1d':
                self.period = 40
                self.std_dev = 2.4
                self.trend_period = 80
    
    def generate_signals(self, df):
        try:
            if len(df) == 0:
                return pd.DataFrame()
                
            signals = pd.DataFrame(index=df.index)
            signals['price'] = df['close']
            
            # Calculate Bollinger Bands
            signals['middle_band'] = signals['price'].rolling(window=self.period, min_periods=1).mean()
            signals['std'] = signals['price'].rolling(window=self.period, min_periods=1).std()
            signals['upper_band'] = signals['middle_band'] + (signals['std'] * self.std_dev)
            signals['lower_band'] = signals['middle_band'] - (signals['std'] * self.std_dev)
            
            # Calculate trend using multiple timeframes
            signals['sma_short'] = signals['price'].rolling(window=self.trend_period//2, min_periods=1).mean()
            signals['sma_long'] = signals['price'].rolling(window=self.trend_period, min_periods=1).mean()
            signals['trend_strength'] = (signals['sma_short'] - signals['sma_long']) / signals['sma_long']
            
            # Calculate volatility
            signals['returns'] = signals['price'].pct_change()
            signals['volatility'] = signals['returns'].rolling(window=self.period, min_periods=1).std()
            signals['volatility_ma'] = signals['volatility'].rolling(window=self.period, min_periods=1).mean()
            
            # Calculate band width
            signals['band_width'] = (signals['upper_band'] - signals['lower_band']) / signals['middle_band']
            signals['band_width_ma'] = signals['band_width'].rolling(window=self.period, min_periods=1).mean()
            
            # Calculate volume metrics
            signals['volume_ma'] = df['volume'].rolling(window=self.period, min_periods=1).mean()
            signals['volume_ratio'] = df['volume'] / signals['volume_ma']
            signals['volume_trend'] = df['volume'].rolling(window=self.period//2, min_periods=1).mean() / \
                                    df['volume'].rolling(window=self.period, min_periods=1).mean()
            
            # Initialize signal column
            signals['signal'] = 0.0
            
            if self.strategy_type == 'breakout':
                # Breakout strategy with trend confirmation
                for idx in df.index:
                    current_price = signals.loc[idx, 'price']
                    current_upper = signals.loc[idx, 'upper_band']
                    current_lower = signals.loc[idx, 'lower_band']
                    current_trend = signals.loc[idx, 'trend_strength']
                    current_volatility = signals.loc[idx, 'volatility']
                    current_volatility_ma = signals.loc[idx, 'volatility_ma']
                    current_band_width = signals.loc[idx, 'band_width']
                    current_band_width_ma = signals.loc[idx, 'band_width_ma']
                    current_volume_ratio = signals.loc[idx, 'volume_ratio']
                    current_volume_trend = signals.loc[idx, 'volume_trend']
                    
                    # Check if volatility is not too high
                    if current_volatility > current_volatility_ma * 1.5:  # Reduced from 2.0
                        continue
                        
                    # Check if band width is not too narrow
                    if current_band_width < current_band_width_ma * 0.3:  # Reduced from 0.5
                        continue
                    
                    # Skip if volume is too low
                    if current_volume_ratio < 1.1 or current_volume_trend < 1.0:  # Reduced thresholds
                        continue
                    
                    # Generate signals with trend confirmation
                    if current_price > current_upper and current_trend > 0.0005:  # Reduced from 0.001
                        signals.loc[idx, 'signal'] = 1.0
                    elif current_price < current_lower and current_trend < -0.0005:  # Reduced from -0.001
                        signals.loc[idx, 'signal'] = -1.0
            else:
                # Mean reversion strategy with trend confirmation
                for idx in df.index:
                    current_price = signals.loc[idx, 'price']
                    current_upper = signals.loc[idx, 'upper_band']
                    current_lower = signals.loc[idx, 'lower_band']
                    current_trend = signals.loc[idx, 'trend_strength']
                    current_volatility = signals.loc[idx, 'volatility']
                    current_volatility_ma = signals.loc[idx, 'volatility_ma']
                    current_band_width = signals.loc[idx, 'band_width']
                    current_band_width_ma = signals.loc[idx, 'band_width_ma']
                    current_volume_ratio = signals.loc[idx, 'volume_ratio']
                    current_volume_trend = signals.loc[idx, 'volume_trend']
                    
                    # Check if volatility is not too high
                    if current_volatility > current_volatility_ma * 1.5:  # Reduced from 2.0
                        continue
                        
                    # Check if band width is not too narrow
                    if current_band_width < current_band_width_ma * 0.3:  # Reduced from 0.5
                        continue
                    
                    # Skip if volume is too low
                    if current_volume_ratio < 1.1 or current_volume_trend < 1.0:  # Reduced thresholds
                        continue
                    
                    # Generate signals with trend confirmation
                    if current_price < current_lower and current_trend > -0.0005:  # Reduced from -0.001
                        signals.loc[idx, 'signal'] = 1.0
                    elif current_price > current_upper and current_trend < 0.0005:  # Reduced from 0.001
                        signals.loc[idx, 'signal'] = -1.0
            
            # Calculate position changes
            signals['position'] = signals['signal'].diff()
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in BollingerBandStrategy: {e}")
            return pd.DataFrame()

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
            signals['signal'] = 0.0
            
            # Find local extrema
            price_minima = self._find_local_minima(df['close'])
            price_maxima = self._find_local_maxima(df['close'])
            rsi_minima = self._find_local_minima(df['rsi'])
            rsi_maxima = self._find_local_maxima(df['rsi'])
            
            # Process bullish divergence (price making lower lows but RSI making higher lows)
            for i in range(len(price_minima)-1):
                if pd.isna(price_minima.iloc[i]) or pd.isna(price_minima.iloc[i+1]):
                    continue
                if pd.isna(rsi_minima.iloc[i]) or pd.isna(rsi_minima.iloc[i+1]):
                    continue
                    
                if price_minima.iloc[i+1] < price_minima.iloc[i] and rsi_minima.iloc[i+1] > rsi_minima.iloc[i]:
                    signals.loc[price_minima.index[i+1], 'signal'] = 1.0
            
            # Process bearish divergence (price making higher highs but RSI making lower highs)
            for i in range(len(price_maxima)-1):
                if pd.isna(price_maxima.iloc[i]) or pd.isna(price_maxima.iloc[i+1]):
                    continue
                if pd.isna(rsi_maxima.iloc[i]) or pd.isna(rsi_maxima.iloc[i+1]):
                    continue
                    
                if price_maxima.iloc[i+1] > price_maxima.iloc[i] and rsi_maxima.iloc[i+1] < rsi_maxima.iloc[i]:
                    signals.loc[price_maxima.index[i+1], 'signal'] = -1.0
            
            # Calculate position changes
            signals['position'] = signals['signal'].diff()
            
            # Log signals
            if (signals['signal'] == 1).any():
                self.logger.info(f"RSIDivergence - BUY signal at: {signals[signals['signal'] == 1].index[-1]}")
            if (signals['signal'] == -1).any():
                self.logger.info(f"RSIDivergence - SELL signal at: {signals[signals['signal'] == -1].index[-1]}")
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in RSIDivergenceStrategy: {e}")
            return pd.DataFrame()

class MomentumStrategy:
    """Enhanced momentum strategy with trend confirmation"""
    
    def __init__(self, period=14, threshold=0.001, trend_period=50, volatility_period=20):
        self.period = period
        self.threshold = threshold
        self.trend_period = trend_period
        self.volatility_period = volatility_period
        self.logger = logging.getLogger(__name__)
        
        # Adjust parameters based on timeframe
        if hasattr(self, 'timeframe'):
            if self.timeframe == '4h':
                self.period = 20
                self.threshold = 0.002
                self.trend_period = 60
            elif self.timeframe == '1d':
                self.period = 30
                self.threshold = 0.003
                self.trend_period = 80
    
    def generate_signals(self, df):
        try:
            if len(df) == 0:
                return pd.DataFrame()
                
            signals = pd.DataFrame(index=df.index)
            signals['price'] = df['close']
            
            # Calculate momentum indicators
            signals['returns'] = df['close'].pct_change(periods=self.period)
            signals['momentum'] = df['close'] - df['close'].shift(self.period)
            signals['momentum_ma'] = signals['momentum'].rolling(window=self.period, min_periods=1).mean()
            
            # Calculate trend using multiple timeframes
            signals['sma_short'] = signals['price'].rolling(window=self.trend_period//2, min_periods=1).mean()
            signals['sma_long'] = signals['price'].rolling(window=self.trend_period, min_periods=1).mean()
            signals['trend_strength'] = (signals['sma_short'] - signals['sma_long']) / signals['sma_long']
            
            # Calculate volatility
            signals['volatility'] = signals['returns'].rolling(window=self.volatility_period, min_periods=1).std()
            signals['volatility_ma'] = signals['volatility'].rolling(window=self.volatility_period, min_periods=1).mean()
            
            # Calculate volume metrics
            signals['volume_ma'] = df['volume'].rolling(window=self.period, min_periods=1).mean()
            signals['volume_ratio'] = df['volume'] / signals['volume_ma']
            signals['volume_trend'] = df['volume'].rolling(window=self.period//2, min_periods=1).mean() / \
                                    df['volume'].rolling(window=self.period, min_periods=1).mean()
            
            # Calculate price acceleration
            signals['acceleration'] = signals['momentum'].diff()
            signals['acceleration_ma'] = signals['acceleration'].rolling(window=self.period, min_periods=1).mean()
            
            # Initialize signal column
            signals['signal'] = 0.0
            
            # Generate signals with enhanced logic
            for idx in df.index:
                current_momentum = signals.loc[idx, 'momentum']
                current_momentum_ma = signals.loc[idx, 'momentum_ma']
                current_trend = signals.loc[idx, 'trend_strength']
                current_volatility = signals.loc[idx, 'volatility']
                current_volatility_ma = signals.loc[idx, 'volatility_ma']
                current_volume_ratio = signals.loc[idx, 'volume_ratio']
                current_volume_trend = signals.loc[idx, 'volume_trend']
                current_acceleration = signals.loc[idx, 'acceleration']
                current_acceleration_ma = signals.loc[idx, 'acceleration_ma']
                
                # Skip if volatility is too high
                if current_volatility > current_volatility_ma * 1.5:  # Reduced from 1.8
                    continue
                
                # Skip if volume is too low
                if current_volume_ratio < 1.1 or current_volume_trend < 1.0:  # Reduced thresholds
                    continue
                
                # Generate signals with trend and acceleration confirmation
                if (current_momentum > self.threshold and  # Removed 1.5x multiplier
                    current_momentum > current_momentum_ma and 
                    current_trend > 0.001 and  # Reduced from 0.002
                    current_acceleration > current_acceleration_ma):
                    signals.loc[idx, 'signal'] = 1.0
                elif (current_momentum < -self.threshold and  # Removed 1.5x multiplier
                      current_momentum < current_momentum_ma and 
                      current_trend < -0.001 and  # Reduced from -0.002
                      current_acceleration < current_acceleration_ma):
                    signals.loc[idx, 'signal'] = -1.0
            
            # Calculate position changes
            signals['position'] = signals['signal'].diff()
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in MomentumStrategy: {e}")
            return pd.DataFrame()

class TrendFollowingStrategy:
    """Enhanced trend following strategy with multiple timeframe confirmation"""
    
    def __init__(self, short_period=10, long_period=30, threshold=0.001, trend_period=50):
        self.short_period = short_period
        self.long_period = long_period
        self.threshold = threshold
        self.trend_period = trend_period
        self.logger = logging.getLogger(__name__)
        
        # Adjust parameters based on timeframe
        if hasattr(self, 'timeframe'):
            if self.timeframe == '4h':
                self.short_period = 15
                self.long_period = 45
                self.threshold = 0.002
                self.trend_period = 60
            elif self.timeframe == '1d':
                self.short_period = 20
                self.long_period = 60
                self.threshold = 0.003
                self.trend_period = 80
    
    def generate_signals(self, df):
        try:
            if len(df) == 0:
                return pd.DataFrame()
                
            signals = pd.DataFrame(index=df.index)
            signals['price'] = df['close']
            
            # Calculate multiple timeframe moving averages
            signals['sma_short'] = df['close'].rolling(window=self.short_period, min_periods=1).mean()
            signals['sma_long'] = df['close'].rolling(window=self.long_period, min_periods=1).mean()
            signals['sma_trend_short'] = df['close'].rolling(window=self.trend_period//2, min_periods=1).mean()
            signals['sma_trend_long'] = df['close'].rolling(window=self.trend_period, min_periods=1).mean()
            
            # Calculate trend strength
            signals['trend_strength'] = (signals['sma_short'] - signals['sma_long']) / signals['sma_long']
            signals['trend_strength_long'] = (signals['sma_trend_short'] - signals['sma_trend_long']) / signals['sma_trend_long']
            
            # Calculate volatility
            signals['returns'] = df['close'].pct_change()
            signals['volatility'] = signals['returns'].rolling(window=self.short_period, min_periods=1).std()
            signals['volatility_ma'] = signals['volatility'].rolling(window=self.long_period, min_periods=1).mean()
            
            # Calculate volume metrics
            signals['volume_ma'] = df['volume'].rolling(window=self.short_period, min_periods=1).mean()
            signals['volume_ratio'] = df['volume'] / signals['volume_ma']
            signals['volume_trend'] = df['volume'].rolling(window=self.short_period, min_periods=1).mean() / \
                                    df['volume'].rolling(window=self.long_period, min_periods=1).mean()
            
            # Calculate price momentum
            signals['momentum'] = signals['price'].pct_change(periods=self.short_period)
            signals['momentum_ma'] = signals['momentum'].rolling(window=self.short_period, min_periods=1).mean()
            
            # Initialize signal column
            signals['signal'] = 0.0
            
            # Generate signals with enhanced logic
            for idx in df.index:
                current_price = signals.loc[idx, 'price']
                current_short_ma = signals.loc[idx, 'sma_short']
                current_long_ma = signals.loc[idx, 'sma_long']
                current_trend = signals.loc[idx, 'trend_strength']
                current_trend_long = signals.loc[idx, 'trend_strength_long']
                current_volatility = signals.loc[idx, 'volatility']
                current_volatility_ma = signals.loc[idx, 'volatility_ma']
                current_volume_ratio = signals.loc[idx, 'volume_ratio']
                current_volume_trend = signals.loc[idx, 'volume_trend']
                current_momentum = signals.loc[idx, 'momentum']
                current_momentum_ma = signals.loc[idx, 'momentum_ma']
                
                # Skip if volatility is too high
                if current_volatility > current_volatility_ma * 1.5:  # Reduced from 1.8
                    continue
                
                # Skip if volume is too low
                if current_volume_ratio < 1.1 or current_volume_trend < 1.0:  # Reduced thresholds
                    continue
                
                # Calculate price deviation from moving averages
                short_deviation = (current_price - current_short_ma) / current_short_ma
                long_deviation = (current_price - current_long_ma) / current_long_ma
                
                # Generate signals with multiple timeframe confirmation
                if (short_deviation > self.threshold and  # Removed 1.5x multiplier
                    long_deviation > self.threshold and  # Removed 1.5x multiplier
                    current_trend > 0.001 and  # Reduced from 0.002
                    current_trend_long > 0.001 and  # Reduced from 0.002
                    current_momentum > current_momentum_ma):
                    signals.loc[idx, 'signal'] = 1.0
                elif (short_deviation < -self.threshold and  # Removed 1.5x multiplier
                      long_deviation < -self.threshold and  # Removed 1.5x multiplier
                      current_trend < -0.001 and  # Reduced from -0.002
                      current_trend_long < -0.001 and  # Reduced from -0.002
                      current_momentum < current_momentum_ma):
                    signals.loc[idx, 'signal'] = -1.0
            
            # Calculate position changes
            signals['position'] = signals['signal'].diff()
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in TrendFollowingStrategy: {e}")
            return pd.DataFrame()