from binance.client import Client
from config import API_KEY, API_SECRET, TESTNET
from trading.strategies import RSIStrategy, RSIDivergenceStrategy, EnhancedRSIStrategy, MovingAverageCrossover, BollingerBandStrategy, MomentumStrategy, TrendFollowingStrategy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Backtester:
    def __init__(self, start_date, end_date, trading_pairs, timeframe='1h', initial_balance=10000):
        self.client = Client(API_KEY, API_SECRET, testnet=TESTNET)
        self.start_date = start_date
        self.end_date = end_date
        self.trading_pairs = trading_pairs
        self.timeframe = timeframe
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.available_balance = initial_balance
        self.unrealized_pnl = 0
        self.max_drawdown = 0
        self.peak_balance = initial_balance
        self.trade_history = []
        self.open_positions = []
        
        # Risk management parameters
        self.max_position_size = 0.1  # Maximum 10% of balance per position
        self.stop_loss_pct = 0.02     # 2% stop loss
        self.take_profit_pct = 0.06   # 6% take profit
        self.max_risk_per_trade = 0.01  # Maximum 1% risk per trade
        self.max_drawdown_limit = 0.2   # Maximum 20% drawdown
        
        # Initialize strategies
        self.strategies = [
            RSIStrategy(),
            RSIDivergenceStrategy(),
            EnhancedRSIStrategy()
        ]
    
    def calculate_rsi(self, data, periods=14):
        """Calculate RSI using pandas"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_ema(self, data, periods):
        """Calculate EMA using pandas"""
        return data.ewm(span=periods, adjust=False).mean()
    
    def calculate_macd(self, data):
        """Calculate MACD using pandas"""
        exp1 = data.ewm(span=12, adjust=False).mean()
        exp2 = data.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist
    
    def calculate_bollinger_bands(self, data, periods=20):
        """Calculate Bollinger Bands using pandas"""
        middle = data.rolling(window=periods).mean()
        std = data.rolling(window=periods).std()
        upper = middle + (std * 2)
        lower = middle - (std * 2)
        return upper, middle, lower
    
    def calculate_atr(self, high, low, close, periods=14):
        """Calculate ATR using pandas"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=periods).mean()
        
    def prepare_data(self, df):
        """Prepare data with technical indicators"""
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Calculate Bollinger Bands
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['std_20'] = df['close'].rolling(window=20).std()
        df['upper_band'] = df['sma_20'] + (df['std_20'] * 2)
        df['lower_band'] = df['sma_20'] - (df['std_20'] * 2)
        
        # Calculate Moving Averages
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # Calculate MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # Calculate Momentum
        df['momentum'] = df['close'].pct_change(periods=14)
        
        # Fill NaN values
        df = df.fillna(method='bfill')
        
        return df
        
    def fetch_historical_data(self, symbol):
        """Fetch historical klines/candlestick data"""
        try:
            logger.info(f"Fetching data for {symbol} from {self.start_date} to {self.end_date}")
            # Get historical klines
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=self.timeframe,
                start_str=int(self.start_date.timestamp() * 1000),
                end_str=int(self.end_date.timestamp() * 1000)
            )
            
            if not klines:
                logger.warning(f"No data available for {symbol}")
                return pd.DataFrame()
            
            logger.info(f"Retrieved {len(klines)} candles for {symbol}")
            
            # Convert to dataframe
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convert string values to float
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"Data range for {symbol}: {df.index[0]} to {df.index[-1]}")
            logger.info(f"Sample data for {symbol}:\n{df[['open', 'high', 'low', 'close', 'volume']].head()}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return pd.DataFrame()
    
    def calculate_position_size(self, price, symbol):
        """Calculate position size based on risk management rules"""
        try:
            # Calculate maximum position size based on available balance
            max_position_value = self.available_balance * self.max_position_size
            
            # Calculate position size in base currency
            position_size = max_position_value / price
            
            # Round to appropriate decimal places based on symbol
            position_size = round(position_size, 6)  # Most crypto pairs use 6 decimal places
            
            # Ensure minimum position size
            min_position_value = self.initial_balance * 0.01  # Minimum 1% of initial balance
            min_position_size = min_position_value / price
            
            return max(position_size, min_position_size)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0
    
    def calculate_fee_adjusted_profit(self, trade):
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

    def update_drawdown(self):
        """Update maximum drawdown"""
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        return current_drawdown <= self.max_drawdown_limit

    def check_stop_loss_take_profit(self, position, current_price):
        """Check if position should be closed due to SL/TP"""
        entry_price = position['entry_price']
        
        # Calculate profit/loss percentage
        pnl_pct = (current_price - entry_price) / entry_price
        
        # Check stop loss
        if pnl_pct <= -self.stop_loss_pct:
            return True, "stop_loss"
        
        # Check take profit
        if pnl_pct >= self.take_profit_pct:
            return True, "take_profit"
        
        return False, None

    def execute_trade(self, symbol, side, price, timestamp, strategy_name):
        """Simulate trade execution with improved risk management"""
        if side == 'BUY':
            # Calculate position size based on risk management
            quantity = self.calculate_position_size(price, symbol)
            
            if quantity <= 0:
                logger.info(f"Skipping trade due to position/risk limits: {symbol} {side}")
                return False
            
            cost = quantity * price
            if cost <= self.available_balance:
                self.available_balance -= cost
                if symbol not in self.positions:
                    self.positions[symbol] = []
                
                self.positions[symbol].append({
                    'quantity': quantity,
                    'entry_price': price,
                    'timestamp': timestamp,
                    'strategy': strategy_name,
                    'unrealized_profit': 0
                })
                logger.info(f"{strategy_name} - {symbol} BUY: {quantity:.8f} @ ${price:.2f}")
                return True
        else:  # SELL
            if symbol in self.positions and self.positions[symbol]:
                position = self.positions[symbol].pop(0)
                quantity = position['quantity']
                entry_price = position['entry_price']
                profit = quantity * (price - entry_price)
                self.current_balance += (quantity * price)
                self.available_balance += (quantity * price)
                
                # Update trade history with more details
                self.trade_history.append({
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': price,
                    'quantity': quantity,
                    'profit': profit,
                    'profit_percent': (profit / (entry_price * quantity)) * 100,
                    'entry_time': position['timestamp'],
                    'exit_time': timestamp,
                    'strategy': strategy_name,
                    'exit_reason': position.get('exit_reason', 'signal')
                })
                
                logger.info(f"{strategy_name} - {symbol} SELL: {quantity:.8f} @ ${price:.2f}, Profit: ${profit:.2f}")
                
                # Check if we should continue trading based on drawdown
                if not self.update_drawdown():
                    logger.warning(f"Maximum drawdown limit reached: {self.max_drawdown:.2%}")
                    return False
                
                return True
        return False

    def update_open_positions(self, symbol, current_price, timestamp):
        """Update unrealized profits for open positions"""
        if symbol not in self.positions:
            return
        
        positions_to_close = []
        for i, position in enumerate(self.positions[symbol]):
            # Calculate unrealized profit
            quantity = position['quantity']
            entry_price = position['entry_price']
            unrealized_profit = quantity * (current_price - entry_price)
            position['unrealized_profit'] = unrealized_profit
            
            # Check stop loss and take profit
            should_close, reason = self.check_stop_loss_take_profit(position, current_price)
            if should_close:
                position['exit_reason'] = reason
                positions_to_close.append(i)
        
        # Close positions that hit SL/TP (in reverse order to maintain index validity)
        for i in sorted(positions_to_close, reverse=True):
            position = self.positions[symbol][i]
            self.execute_trade(symbol, 'SELL', current_price, timestamp, position['strategy'])

    def generate_performance_report(self):
        """Generate detailed performance metrics"""
        logger.info("Generating performance report...")
        
        # Overall performance
        total_profit = sum(trade.get('profit', 0) for trade in self.trade_history)
        total_fee_adjusted_profit = sum(self.calculate_fee_adjusted_profit(trade) for trade in self.trade_history)
        total_trades = len(self.trade_history)
        winning_trades = len([t for t in self.trade_history if t.get('profit', 0) > 0])
        
        print("\n=== Account Performance ===")
        print(f"Initial Balance: ${self.initial_balance:.2f}")
        print(f"Current Balance: ${self.current_balance:.2f}")
        print(f"Available Balance: ${self.available_balance:.2f}")
        print(f"Unrealized Profit/Loss: ${self.unrealized_pnl:.2f}")
        print(f"Total Value: ${self.current_balance + self.unrealized_pnl:.2f}")
        print(f"Return: {((self.current_balance - self.initial_balance) / self.initial_balance * 100):.2f}%")
        print(f"Maximum Drawdown: {self.max_drawdown:.2f}%")
        
        print("\n=== Trade Performance ===")
        print(f"Total Realized Profit: ${total_profit:.2f}")
        print(f"Total Realized Profit (After Fees): ${total_fee_adjusted_profit:.2f}")
        print(f"Open Positions: {len(self.open_positions)}")
        print(f"Total Completed Trades: {total_trades}")
        
        if total_trades > 0:
            win_rate = (winning_trades / total_trades * 100)
            print(f"Win Rate: {win_rate:.2f}% ({winning_trades}/{total_trades})")
            
            # Calculate performance by symbol and strategy
            performance_by_pair = {}
            for trade in self.trade_history:
                symbol = trade['symbol']
                strategy = trade['strategy']
                profit = trade.get('profit', 0)
                fee_adjusted_profit = self.calculate_fee_adjusted_profit(trade)
                
                if symbol not in performance_by_pair:
                    performance_by_pair[symbol] = {}
                
                if strategy not in performance_by_pair[symbol]:
                    performance_by_pair[symbol][strategy] = {
                        'total_profit': 0,
                        'fee_adjusted_profit': 0,
                        'trades': 0,
                        'winning_trades': 0
                    }
                
                perf = performance_by_pair[symbol][strategy]
                perf['total_profit'] += profit
                perf['fee_adjusted_profit'] += fee_adjusted_profit
                perf['trades'] += 1
                if profit > 0:
                    perf['winning_trades'] += 1
            
            # Print performance by pair
            print("\n=== Performance by Trading Pair ===")
            print(f"{'Symbol':<10} {'Strategy':<20} {'Total Profit':<12} {'After Fees':<12} {'Win Rate':<10} {'Trades'}")
            print("-" * 80)
            
            sorted_performance = []
            for symbol, strategies in performance_by_pair.items():
                for strategy, perf in strategies.items():
                    win_rate = (perf['winning_trades'] / perf['trades'] * 100) if perf['trades'] > 0 else 0
                    sorted_performance.append({
                        'symbol': symbol,
                        'strategy': strategy,
                        'total_profit': perf['total_profit'],
                        'fee_adjusted_profit': perf['fee_adjusted_profit'],
                        'win_rate': win_rate,
                        'trades': perf['trades']
                    })
            
            # Sort by total profit
            sorted_performance.sort(key=lambda x: x['total_profit'], reverse=True)
            
            for perf in sorted_performance:
                print(f"{perf['symbol']:<10} {perf['strategy']:<20} "
                      f"${perf['total_profit']:<12.2f} ${perf['fee_adjusted_profit']:<12.2f} "
                      f"{perf['win_rate']:<10.2f}% {perf['trades']}")
            
            return performance_by_pair
        else:
            print("No trades executed during the test period.")
            return {}

    def run_backtest(self):
        """Run backtest for all trading pairs and strategies"""
        logger.info("Starting backtest...")
        
        # Initialize trade history for the entire backtest
        self.trade_history = []
        
        for symbol in self.trading_pairs:
            logger.info(f"\n=== Processing {symbol} ===")
            df = self.fetch_historical_data(symbol)
            
            if df.empty:
                logger.warning(f"Skipping {symbol} - no data available")
                continue
                
            logger.info(f"Running strategies for {symbol}")
            
            # Prepare data with technical indicators
            df = self.prepare_data(df)
            
            # Run each strategy
            for strategy in self.strategies:
                strategy_name = strategy.__class__.__name__
                logger.info(f"\nRunning {strategy_name} on {symbol}")
                
                try:
                    signals = strategy.generate_signals(df)
                    
                    if signals.empty:
                        logger.warning(f"No signals generated for {symbol} using {strategy_name}")
                        continue
                        
                    # Log signal statistics
                    total_signals = len(signals[signals['signal'] != 0])
                    buy_signals = len(signals[signals['signal'] > 0])
                    sell_signals = len(signals[signals['signal'] < 0])
                    
                    logger.info(f"{strategy_name} on {symbol} generated:")
                    logger.info(f"- Total signals: {total_signals}")
                    logger.info(f"- Buy signals: {buy_signals}")
                    logger.info(f"- Sell signals: {sell_signals}")
                    
                    if total_signals > 0:
                        logger.info(f"Sample signals for {strategy_name} on {symbol}:\n{signals[signals['signal'] != 0].head()}")
                    
                    # Ensure signals DataFrame has required columns
                    if 'signal' not in signals.columns:
                        signals['signal'] = 0
                    
                    # Generate buy/sell signals
                    signals['buy'] = signals['signal'] > 0
                    signals['sell'] = signals['signal'] < 0
                    
                    # Execute trades based on signals
                    position = 0  # 0 = no position, 1 = long position
                    entry_price = 0
                    
                    for i in range(len(signals)):
                        if position == 0 and signals['buy'].iloc[i]:
                            # Calculate position size
                            price = df['close'].iloc[i]
                            position_size = self.calculate_position_size(price, symbol)
                            
                            if position_size > 0:
                                # Enter long position
                                entry_price = price
                                position = 1
                                
                                # Record trade
                                self.trade_history.append({
                                    'symbol': symbol,
                                    'strategy': strategy_name,
                                    'entry_time': df.index[i],
                                    'entry_price': entry_price,
                                    'position_size': position_size,
                                    'type': 'long'
                                })
                                
                                logger.info(f"{strategy_name} - {symbol} BUY: {position_size:.8f} @ ${price:.2f}")
                                
                        elif position == 1 and signals['sell'].iloc[i]:
                            # Exit long position
                            exit_price = df['close'].iloc[i]
                            profit = (exit_price - entry_price) * position_size
                            
                            # Update trade record
                            self.trade_history[-1].update({
                                'exit_time': df.index[i],
                                'exit_price': exit_price,
                                'profit': profit
                            })
                            
                            logger.info(f"{strategy_name} - {symbol} SELL: {position_size:.8f} @ ${exit_price:.2f}, Profit: ${profit:.2f}")
                            
                            # Reset position
                            position = 0
                            entry_price = 0
                            
                            # Update account balance
                            self.current_balance += profit
                            
                except Exception as e:
                    logger.error(f"Error running {strategy_name} on {symbol}: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    continue
            
            logger.info(f"Completed processing {symbol} - Total trades: {len(self.trade_history)}")

def main():
    # Define trading pairs (only those available during our test periods)
    trading_pairs = [
        # Major Cryptos
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT',
        # DeFi and Layer 1
        'LINKUSDT', 'ADAUSDT', 'DOTUSDT', 'SOLUSDT'
    ]
    
    # Define time periods to test - only last 3 months
    time_periods = [
        {
            'name': 'Last 3 Months',
            'start': datetime.now() - timedelta(days=90),
            'end': datetime.now()
        }
    ]
    
    # Define timeframes to test
    timeframes = ['1h', '4h', '1d']
    
    # Initialize results storage
    all_results = []
    
    # Run backtests for each combination
    for period in time_periods:
        print(f"\n=== Testing Period: {period['name']} ===")
        print(f"From: {period['start']} To: {period['end']}")
        
        for timeframe in timeframes:
            print(f"\n--- Timeframe: {timeframe} ---")
            
            # Initialize and run backtest with more active strategies
            backtester = Backtester(
                start_date=period['start'],
                end_date=period['end'],
                trading_pairs=trading_pairs,
                timeframe=timeframe
            )
            
            # Add extremely aggressive strategies
            backtester.strategies = [
                # Existing strategies with ultra-aggressive parameters
                RSIStrategy(rsi_period=3, overbought=55, oversold=45),  # Ultra tight RSI range
                RSIDivergenceStrategy(rsi_period=3, divergence_threshold=0.001),  # Ultra sensitive
                EnhancedRSIStrategy(
                    rsi_period=3,
                    oversold_threshold=45,
                    overbought_threshold=55,
                    volatility_factor=0.01,  # Minimal volatility impact
                    trend_period=3
                ),
                # Simple price action strategies that should work on all pairs
                MovingAverageCrossover(short_window=2, long_window=5),  # Ultra short-term MA crossover
                BollingerBandStrategy(strategy_type='breakout'),  # Breakout strategy
                BollingerBandStrategy(strategy_type='reversion'),  # Mean reversion strategy
                # Add simple momentum strategy
                MomentumStrategy(period=3, threshold=0.001),  # Very sensitive to price changes
                # Add simple trend following strategy
                TrendFollowingStrategy(period=3, threshold=0.001)  # Very sensitive to trends
            ]
            
            # Adjust risk management to allow more trades
            backtester.max_position_size = 0.5  # Allow up to 50% of balance per position
            backtester.stop_loss_pct = 0.01     # 1% stop loss
            backtester.take_profit_pct = 0.02   # 2% take profit
            backtester.max_risk_per_trade = 0.05  # Allow 5% risk per trade
            
            backtester.run_backtest()
            results = backtester.generate_performance_report()
            
            # Store results
            all_results.append({
                'period': period['name'],
                'timeframe': timeframe,
                'start_date': period['start'],
                'end_date': period['end'],
                'total_profit': backtester.current_balance - backtester.initial_balance,
                'win_rate': len([t for t in backtester.trade_history if t.get('profit', 0) > 0]) / len(backtester.trade_history) * 100 if backtester.trade_history else 0,
                'trades': len(backtester.trade_history),
                'trade_history': backtester.trade_history  # Store the actual trade history
            })
    
    # Generate summary report
    print("\n=== Summary Report ===")
    print("Period          Timeframe  Pair         Strategy        Profit    After Fees  Win Rate  Trades")
    print("-" * 100)
    
    # Create a flattened list of all results for sorting
    flattened_results = []
    for result in all_results:
        # Group trades by pair and strategy
        pair_strategy_trades = {}
        for trade in result['trade_history']:
            key = (trade['symbol'], trade['strategy'])
            if key not in pair_strategy_trades:
                pair_strategy_trades[key] = {
                    'trades': [],
                    'total_profit': 0,
                    'winning_trades': 0
                }
            pair_strategy_trades[key]['trades'].append(trade)
            pair_strategy_trades[key]['total_profit'] += trade.get('profit', 0)
            if trade.get('profit', 0) > 0:
                pair_strategy_trades[key]['winning_trades'] += 1
        
        # Add results for each pair/strategy combination
        for (symbol, strategy), data in pair_strategy_trades.items():
            total_trades = len(data['trades'])
            win_rate = (data['winning_trades'] / total_trades * 100) if total_trades > 0 else 0
            fee_adjusted_profit = data['total_profit'] * 0.998  # 0.1% fee per trade (entry and exit)
            
            flattened_results.append({
                'period': result['period'],
                'timeframe': result['timeframe'],
                'symbol': symbol,
                'strategy': strategy,
                'total_profit': data['total_profit'],
                'fee_adjusted_profit': fee_adjusted_profit,
                'win_rate': win_rate,
                'trades': total_trades
            })
        
        # Add entries for pairs with no trades
        for symbol in trading_pairs:
            has_trades = any(trade['symbol'] == symbol for trade in result['trade_history'])
            if not has_trades:
                flattened_results.append({
                    'period': result['period'],
                    'timeframe': result['timeframe'],
                    'symbol': symbol,
                    'strategy': 'No Trades',
                    'total_profit': 0,
                    'fee_adjusted_profit': 0,
                    'win_rate': 0,
                    'trades': 0
                })
    
    # Sort by fee adjusted profit
    flattened_results.sort(key=lambda x: x['fee_adjusted_profit'], reverse=True)
    
    # Print sorted results
    for result in flattened_results:
        print(f"{result['period']:<15} {result['timeframe']:<10} "
              f"{result['symbol']:<12} {result['strategy']:<15} "
              f"${result['total_profit']:<9.2f} ${result['fee_adjusted_profit']:<11.2f} "
              f"{result['win_rate']:<9.2f}% {result['trades']}")

if __name__ == "__main__":
    main() 