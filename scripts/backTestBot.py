import os
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
import time
from tqdm import tqdm  # For progress bars

# Set the run name for Firestore
os.environ['RUN_NAME'] = 'backTestBot'

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from binance.client import Client
from config.config import API_KEY, API_SECRET, TESTNET, INITIAL_BALANCE
from trading.strategies import RSIStrategy, RSIDivergenceStrategy, EnhancedRSIStrategy, LiveReactiveRSIStrategy, MovingAverageCrossover, BollingerBandStrategy, MomentumStrategy, TrendFollowingStrategy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

from utils.indicators import calculate_rsi, calculate_ema, calculate_macd, calculate_bollinger_bands, calculate_atr
from utils.backtest_utils import prepare_data, calculate_position_size, calculate_fee_adjusted_profit, check_stop_loss_take_profit
from utils.performance_utils import generate_performance_report, save_trade_history, load_trade_history, export_summary_to_csv, export_daily_summary_to_csv, export_aggregated_summary_to_csv
from utils.trade_utils import execute_trade, update_open_positions
from utils.database import TradingDatabase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Filter out specific warnings
logging.getLogger('backTestBot').setLevel(logging.ERROR)

# ===== BACKTEST CONFIGURATION =====
# Define all backtest combinations to run
# Format: (symbol, strategy_name, timeframe)
BACKTEST_COMBOS = [
    # USDT pairs
    # BTCUSDT combinations
    ("BTCUSDT", "RSIStrategy", "15m"),
    ("BTCUSDT", "RSIStrategy", "30m"),
    ("BTCUSDT", "RSIStrategy", "1h"),
    ("BTCUSDT", "RSIStrategy", "2h"),
    ("BTCUSDT", "RSIStrategy", "4h"),
    ("BTCUSDT", "RSIStrategy", "1d"),
    ("BTCUSDT", "EnhancedRSIStrategy", "15m"),
    ("BTCUSDT", "EnhancedRSIStrategy", "30m"),
    ("BTCUSDT", "EnhancedRSIStrategy", "1h"),
    ("BTCUSDT", "EnhancedRSIStrategy", "2h"),
    ("BTCUSDT", "EnhancedRSIStrategy", "4h"),
    ("BTCUSDT", "EnhancedRSIStrategy", "1d"),
    ("BTCUSDT", "RSIDivergenceStrategy", "15m"),
    ("BTCUSDT", "RSIDivergenceStrategy", "30m"),
    ("BTCUSDT", "RSIDivergenceStrategy", "1h"),
    ("BTCUSDT", "RSIDivergenceStrategy", "2h"),
    ("BTCUSDT", "RSIDivergenceStrategy", "4h"),
    ("BTCUSDT", "RSIDivergenceStrategy", "1d"),
    ("BTCUSDT", "MovingAverageCrossover", "15m"),
    ("BTCUSDT", "MovingAverageCrossover", "30m"),
    ("BTCUSDT", "MovingAverageCrossover", "1h"),
    ("BTCUSDT", "MovingAverageCrossover", "2h"),
    ("BTCUSDT", "MovingAverageCrossover", "4h"),
    ("BTCUSDT", "MovingAverageCrossover", "1d"),
    ("BTCUSDT", "BollingerBandStrategy", "15m"),
    ("BTCUSDT", "BollingerBandStrategy", "30m"),
    ("BTCUSDT", "BollingerBandStrategy", "1h"),
    ("BTCUSDT", "BollingerBandStrategy", "2h"),
    ("BTCUSDT", "BollingerBandStrategy", "4h"),
    ("BTCUSDT", "BollingerBandStrategy", "1d"),
    ("BTCUSDT", "MomentumStrategy", "15m"),
    ("BTCUSDT", "MomentumStrategy", "30m"),
    ("BTCUSDT", "MomentumStrategy", "1h"),
    ("BTCUSDT", "MomentumStrategy", "2h"),
    ("BTCUSDT", "MomentumStrategy", "4h"),
    ("BTCUSDT", "MomentumStrategy", "1d"),
    ("BTCUSDT", "TrendFollowingStrategy", "15m"),
    ("BTCUSDT", "TrendFollowingStrategy", "30m"),
    ("BTCUSDT", "TrendFollowingStrategy", "1h"),
    ("BTCUSDT", "TrendFollowingStrategy", "2h"),
    ("BTCUSDT", "TrendFollowingStrategy", "4h"),
    ("BTCUSDT", "TrendFollowingStrategy", "1d"),
    ("BTCUSDT", "LiveReactiveRSIStrategy", "15m"),
    ("BTCUSDT", "LiveReactiveRSIStrategy", "30m"),
    ("BTCUSDT", "LiveReactiveRSIStrategy", "1h"),
    ("BTCUSDT", "LiveReactiveRSIStrategy", "2h"),
    ("BTCUSDT", "LiveReactiveRSIStrategy", "4h"),
    ("BTCUSDT", "LiveReactiveRSIStrategy", "1d"),

    # ETHUSDT combinations
    ("ETHUSDT", "RSIStrategy", "15m"),
    ("ETHUSDT", "RSIStrategy", "30m"),
    ("ETHUSDT", "RSIStrategy", "1h"),
    ("ETHUSDT", "RSIStrategy", "2h"),
    ("ETHUSDT", "RSIStrategy", "4h"),
    ("ETHUSDT", "RSIStrategy", "1d"),
    ("ETHUSDT", "EnhancedRSIStrategy", "15m"),
    ("ETHUSDT", "EnhancedRSIStrategy", "30m"),
    ("ETHUSDT", "EnhancedRSIStrategy", "1h"),
    ("ETHUSDT", "EnhancedRSIStrategy", "2h"),
    ("ETHUSDT", "EnhancedRSIStrategy", "4h"),
    ("ETHUSDT", "EnhancedRSIStrategy", "1d"),
    ("ETHUSDT", "RSIDivergenceStrategy", "15m"),
    ("ETHUSDT", "RSIDivergenceStrategy", "30m"),
    ("ETHUSDT", "RSIDivergenceStrategy", "1h"),
    ("ETHUSDT", "RSIDivergenceStrategy", "2h"),
    ("ETHUSDT", "RSIDivergenceStrategy", "4h"),
    ("ETHUSDT", "RSIDivergenceStrategy", "1d"),
    ("ETHUSDT", "MovingAverageCrossover", "15m"),
    ("ETHUSDT", "MovingAverageCrossover", "30m"),
    ("ETHUSDT", "MovingAverageCrossover", "1h"),
    ("ETHUSDT", "MovingAverageCrossover", "2h"),
    ("ETHUSDT", "MovingAverageCrossover", "4h"),
    ("ETHUSDT", "MovingAverageCrossover", "1d"),
    ("ETHUSDT", "BollingerBandStrategy", "15m"),
    ("ETHUSDT", "BollingerBandStrategy", "30m"),
    ("ETHUSDT", "BollingerBandStrategy", "1h"),
    ("ETHUSDT", "BollingerBandStrategy", "2h"),
    ("ETHUSDT", "BollingerBandStrategy", "4h"),
    ("ETHUSDT", "BollingerBandStrategy", "1d"),
    ("ETHUSDT", "MomentumStrategy", "15m"),
    ("ETHUSDT", "MomentumStrategy", "30m"),
    ("ETHUSDT", "MomentumStrategy", "1h"),
    ("ETHUSDT", "MomentumStrategy", "2h"),
    ("ETHUSDT", "MomentumStrategy", "4h"),
    ("ETHUSDT", "MomentumStrategy", "1d"),
    ("ETHUSDT", "TrendFollowingStrategy", "15m"),
    ("ETHUSDT", "TrendFollowingStrategy", "30m"),
    ("ETHUSDT", "TrendFollowingStrategy", "1h"),
    ("ETHUSDT", "TrendFollowingStrategy", "2h"),
    ("ETHUSDT", "TrendFollowingStrategy", "4h"),
    ("ETHUSDT", "TrendFollowingStrategy", "1d"),
    ("ETHUSDT", "LiveReactiveRSIStrategy", "15m"),
    ("ETHUSDT", "LiveReactiveRSIStrategy", "30m"),
    ("ETHUSDT", "LiveReactiveRSIStrategy", "1h"),
    ("ETHUSDT", "LiveReactiveRSIStrategy", "2h"),
    ("ETHUSDT", "LiveReactiveRSIStrategy", "4h"),
    ("ETHUSDT", "LiveReactiveRSIStrategy", "1d"),

    # BNBUSDT combinations
    ("BNBUSDT", "RSIStrategy", "15m"),
    ("BNBUSDT", "RSIStrategy", "30m"),
    ("BNBUSDT", "RSIStrategy", "1h"),
    ("BNBUSDT", "RSIStrategy", "2h"),
    ("BNBUSDT", "RSIStrategy", "4h"),
    ("BNBUSDT", "RSIStrategy", "1d"),
    ("BNBUSDT", "EnhancedRSIStrategy", "15m"),
    ("BNBUSDT", "EnhancedRSIStrategy", "30m"),
    ("BNBUSDT", "EnhancedRSIStrategy", "1h"),
    ("BNBUSDT", "EnhancedRSIStrategy", "2h"),
    ("BNBUSDT", "EnhancedRSIStrategy", "4h"),
    ("BNBUSDT", "EnhancedRSIStrategy", "1d"),
    ("BNBUSDT", "RSIDivergenceStrategy", "15m"),
    ("BNBUSDT", "RSIDivergenceStrategy", "30m"),
    ("BNBUSDT", "RSIDivergenceStrategy", "1h"),
    ("BNBUSDT", "RSIDivergenceStrategy", "2h"),
    ("BNBUSDT", "RSIDivergenceStrategy", "4h"),
    ("BNBUSDT", "RSIDivergenceStrategy", "1d"),
    ("BNBUSDT", "MovingAverageCrossover", "15m"),
    ("BNBUSDT", "MovingAverageCrossover", "30m"),
    ("BNBUSDT", "MovingAverageCrossover", "1h"),
    ("BNBUSDT", "MovingAverageCrossover", "2h"),
    ("BNBUSDT", "MovingAverageCrossover", "4h"),
    ("BNBUSDT", "MovingAverageCrossover", "1d"),
    ("BNBUSDT", "BollingerBandStrategy", "15m"),
    ("BNBUSDT", "BollingerBandStrategy", "30m"),
    ("BNBUSDT", "BollingerBandStrategy", "1h"),
    ("BNBUSDT", "BollingerBandStrategy", "2h"),
    ("BNBUSDT", "BollingerBandStrategy", "4h"),
    ("BNBUSDT", "BollingerBandStrategy", "1d"),
    ("BNBUSDT", "MomentumStrategy", "15m"),
    ("BNBUSDT", "MomentumStrategy", "30m"),
    ("BNBUSDT", "MomentumStrategy", "1h"),
    ("BNBUSDT", "MomentumStrategy", "2h"),
    ("BNBUSDT", "MomentumStrategy", "4h"),
    ("BNBUSDT", "MomentumStrategy", "1d"),
    ("BNBUSDT", "TrendFollowingStrategy", "15m"),
    ("BNBUSDT", "TrendFollowingStrategy", "30m"),
    ("BNBUSDT", "TrendFollowingStrategy", "1h"),
    ("BNBUSDT", "TrendFollowingStrategy", "2h"),
    ("BNBUSDT", "TrendFollowingStrategy", "4h"),
    ("BNBUSDT", "TrendFollowingStrategy", "1d"),
    ("BNBUSDT", "LiveReactiveRSIStrategy", "15m"),
    ("BNBUSDT", "LiveReactiveRSIStrategy", "30m"),
    ("BNBUSDT", "LiveReactiveRSIStrategy", "1h"),
    ("BNBUSDT", "LiveReactiveRSIStrategy", "2h"),
    ("BNBUSDT", "LiveReactiveRSIStrategy", "4h"),
    ("BNBUSDT", "LiveReactiveRSIStrategy", "1d"),

    # ADAUSDT combinations
    ("ADAUSDT", "RSIStrategy", "15m"),
    ("ADAUSDT", "RSIStrategy", "30m"),
    ("ADAUSDT", "RSIStrategy", "1h"),
    ("ADAUSDT", "RSIStrategy", "2h"),
    ("ADAUSDT", "RSIStrategy", "4h"),
    ("ADAUSDT", "RSIStrategy", "1d"),
    ("ADAUSDT", "EnhancedRSIStrategy", "15m"),
    ("ADAUSDT", "EnhancedRSIStrategy", "30m"),
    ("ADAUSDT", "EnhancedRSIStrategy", "1h"),
    ("ADAUSDT", "EnhancedRSIStrategy", "2h"),
    ("ADAUSDT", "EnhancedRSIStrategy", "4h"),
    ("ADAUSDT", "EnhancedRSIStrategy", "1d"),
    ("ADAUSDT", "RSIDivergenceStrategy", "15m"),
    ("ADAUSDT", "RSIDivergenceStrategy", "30m"),
    ("ADAUSDT", "RSIDivergenceStrategy", "1h"),
    ("ADAUSDT", "RSIDivergenceStrategy", "2h"),
    ("ADAUSDT", "RSIDivergenceStrategy", "4h"),
    ("ADAUSDT", "RSIDivergenceStrategy", "1d"),
    ("ADAUSDT", "MovingAverageCrossover", "15m"),
    ("ADAUSDT", "MovingAverageCrossover", "30m"),
    ("ADAUSDT", "MovingAverageCrossover", "1h"),
    ("ADAUSDT", "MovingAverageCrossover", "2h"),
    ("ADAUSDT", "MovingAverageCrossover", "4h"),
    ("ADAUSDT", "MovingAverageCrossover", "1d"),
    ("ADAUSDT", "BollingerBandStrategy", "15m"),
    ("ADAUSDT", "BollingerBandStrategy", "30m"),
    ("ADAUSDT", "BollingerBandStrategy", "1h"),
    ("ADAUSDT", "BollingerBandStrategy", "2h"),
    ("ADAUSDT", "BollingerBandStrategy", "4h"),
    ("ADAUSDT", "BollingerBandStrategy", "1d"),
    ("ADAUSDT", "MomentumStrategy", "15m"),
    ("ADAUSDT", "MomentumStrategy", "30m"),
    ("ADAUSDT", "MomentumStrategy", "1h"),
    ("ADAUSDT", "MomentumStrategy", "2h"),
    ("ADAUSDT", "MomentumStrategy", "4h"),
    ("ADAUSDT", "MomentumStrategy", "1d"),
    ("ADAUSDT", "TrendFollowingStrategy", "15m"),
    ("ADAUSDT", "TrendFollowingStrategy", "30m"),
    ("ADAUSDT", "TrendFollowingStrategy", "1h"),
    ("ADAUSDT", "TrendFollowingStrategy", "2h"),
    ("ADAUSDT", "TrendFollowingStrategy", "4h"),
    ("ADAUSDT", "TrendFollowingStrategy", "1d"),
    ("ADAUSDT", "LiveReactiveRSIStrategy", "15m"),
    ("ADAUSDT", "LiveReactiveRSIStrategy", "30m"),
    ("ADAUSDT", "LiveReactiveRSIStrategy", "1h"),
    ("ADAUSDT", "LiveReactiveRSIStrategy", "2h"),
    ("ADAUSDT", "LiveReactiveRSIStrategy", "4h"),
    ("ADAUSDT", "LiveReactiveRSIStrategy", "1d"),

    # DOGEUSDT combinations
    ("DOGEUSDT", "RSIStrategy", "15m"),
    ("DOGEUSDT", "RSIStrategy", "30m"),
    ("DOGEUSDT", "RSIStrategy", "1h"),
    ("DOGEUSDT", "RSIStrategy", "2h"),
    ("DOGEUSDT", "RSIStrategy", "4h"),
    ("DOGEUSDT", "RSIStrategy", "1d"),
    ("DOGEUSDT", "EnhancedRSIStrategy", "15m"),
    ("DOGEUSDT", "EnhancedRSIStrategy", "30m"),
    ("DOGEUSDT", "EnhancedRSIStrategy", "1h"),
    ("DOGEUSDT", "EnhancedRSIStrategy", "2h"),
    ("DOGEUSDT", "EnhancedRSIStrategy", "4h"),
    ("DOGEUSDT", "EnhancedRSIStrategy", "1d"),
    ("DOGEUSDT", "RSIDivergenceStrategy", "15m"),
    ("DOGEUSDT", "RSIDivergenceStrategy", "30m"),
    ("DOGEUSDT", "RSIDivergenceStrategy", "1h"),
    ("DOGEUSDT", "RSIDivergenceStrategy", "2h"),
    ("DOGEUSDT", "RSIDivergenceStrategy", "4h"),
    ("DOGEUSDT", "RSIDivergenceStrategy", "1d"),
    ("DOGEUSDT", "MovingAverageCrossover", "15m"),
    ("DOGEUSDT", "MovingAverageCrossover", "30m"),
    ("DOGEUSDT", "MovingAverageCrossover", "1h"),
    ("DOGEUSDT", "MovingAverageCrossover", "2h"),
    ("DOGEUSDT", "MovingAverageCrossover", "4h"),
    ("DOGEUSDT", "MovingAverageCrossover", "1d"),
    ("DOGEUSDT", "BollingerBandStrategy", "15m"),
    ("DOGEUSDT", "BollingerBandStrategy", "30m"),
    ("DOGEUSDT", "BollingerBandStrategy", "1h"),
    ("DOGEUSDT", "BollingerBandStrategy", "2h"),
    ("DOGEUSDT", "BollingerBandStrategy", "4h"),
    ("DOGEUSDT", "BollingerBandStrategy", "1d"),
    ("DOGEUSDT", "MomentumStrategy", "15m"),
    ("DOGEUSDT", "MomentumStrategy", "30m"),
    ("DOGEUSDT", "MomentumStrategy", "1h"),
    ("DOGEUSDT", "MomentumStrategy", "2h"),
    ("DOGEUSDT", "MomentumStrategy", "4h"),
    ("DOGEUSDT", "MomentumStrategy", "1d"),
    ("DOGEUSDT", "TrendFollowingStrategy", "15m"),
    ("DOGEUSDT", "TrendFollowingStrategy", "30m"),
    ("DOGEUSDT", "TrendFollowingStrategy", "1h"),
    ("DOGEUSDT", "TrendFollowingStrategy", "2h"),
    ("DOGEUSDT", "TrendFollowingStrategy", "4h"),
    ("DOGEUSDT", "TrendFollowingStrategy", "1d"),
    ("DOGEUSDT", "LiveReactiveRSIStrategy", "15m"),
    ("DOGEUSDT", "LiveReactiveRSIStrategy", "30m"),
    ("DOGEUSDT", "LiveReactiveRSIStrategy", "1h"),
    ("DOGEUSDT", "LiveReactiveRSIStrategy", "2h"),
    ("DOGEUSDT", "LiveReactiveRSIStrategy", "4h"),
    ("DOGEUSDT", "LiveReactiveRSIStrategy", "1d"),

    # XRPUSDT combinations
    ("XRPUSDT", "RSIStrategy", "15m"),
    ("XRPUSDT", "RSIStrategy", "30m"),
    ("XRPUSDT", "RSIStrategy", "1h"),
    ("XRPUSDT", "RSIStrategy", "2h"),
    ("XRPUSDT", "RSIStrategy", "4h"),
    ("XRPUSDT", "RSIStrategy", "1d"),
    ("XRPUSDT", "EnhancedRSIStrategy", "15m"),
    ("XRPUSDT", "EnhancedRSIStrategy", "30m"),
    ("XRPUSDT", "EnhancedRSIStrategy", "1h"),
    ("XRPUSDT", "EnhancedRSIStrategy", "2h"),
    ("XRPUSDT", "EnhancedRSIStrategy", "4h"),
    ("XRPUSDT", "EnhancedRSIStrategy", "1d"),
    ("XRPUSDT", "RSIDivergenceStrategy", "15m"),
    ("XRPUSDT", "RSIDivergenceStrategy", "30m"),
    ("XRPUSDT", "RSIDivergenceStrategy", "1h"),
    ("XRPUSDT", "RSIDivergenceStrategy", "2h"),
    ("XRPUSDT", "RSIDivergenceStrategy", "4h"),
    ("XRPUSDT", "RSIDivergenceStrategy", "1d"),
    ("XRPUSDT", "MovingAverageCrossover", "15m"),
    ("XRPUSDT", "MovingAverageCrossover", "30m"),
    ("XRPUSDT", "MovingAverageCrossover", "1h"),
    ("XRPUSDT", "MovingAverageCrossover", "2h"),
    ("XRPUSDT", "MovingAverageCrossover", "4h"),
    ("XRPUSDT", "MovingAverageCrossover", "1d"),
    ("XRPUSDT", "BollingerBandStrategy", "15m"),
    ("XRPUSDT", "BollingerBandStrategy", "30m"),
    ("XRPUSDT", "BollingerBandStrategy", "1h"),
    ("XRPUSDT", "BollingerBandStrategy", "2h"),
    ("XRPUSDT", "BollingerBandStrategy", "4h"),
    ("XRPUSDT", "BollingerBandStrategy", "1d"),
    ("XRPUSDT", "MomentumStrategy", "15m"),
    ("XRPUSDT", "MomentumStrategy", "30m"),
    ("XRPUSDT", "MomentumStrategy", "1h"),
    ("XRPUSDT", "MomentumStrategy", "2h"),
    ("XRPUSDT", "MomentumStrategy", "4h"),
    ("XRPUSDT", "MomentumStrategy", "1d"),
    ("XRPUSDT", "TrendFollowingStrategy", "15m"),
    ("XRPUSDT", "TrendFollowingStrategy", "30m"),
    ("XRPUSDT", "TrendFollowingStrategy", "1h"),
    ("XRPUSDT", "TrendFollowingStrategy", "2h"),
    ("XRPUSDT", "TrendFollowingStrategy", "4h"),
    ("XRPUSDT", "TrendFollowingStrategy", "1d"),
    ("XRPUSDT", "LiveReactiveRSIStrategy", "15m"),
    ("XRPUSDT", "LiveReactiveRSIStrategy", "30m"),
    ("XRPUSDT", "LiveReactiveRSIStrategy", "1h"),
    ("XRPUSDT", "LiveReactiveRSIStrategy", "2h"),
    ("XRPUSDT", "LiveReactiveRSIStrategy", "4h"),
    ("XRPUSDT", "LiveReactiveRSIStrategy", "1d"),

    # DOTUSDT combinations
    ("DOTUSDT", "RSIStrategy", "15m"),
    ("DOTUSDT", "RSIStrategy", "30m"),
    ("DOTUSDT", "RSIStrategy", "1h"),
    ("DOTUSDT", "RSIStrategy", "2h"),
    ("DOTUSDT", "RSIStrategy", "4h"),
    ("DOTUSDT", "RSIStrategy", "1d"),
    ("DOTUSDT", "EnhancedRSIStrategy", "15m"),
    ("DOTUSDT", "EnhancedRSIStrategy", "30m"),
    ("DOTUSDT", "EnhancedRSIStrategy", "1h"),
    ("DOTUSDT", "EnhancedRSIStrategy", "2h"),
    ("DOTUSDT", "EnhancedRSIStrategy", "4h"),
    ("DOTUSDT", "EnhancedRSIStrategy", "1d"),
    ("DOTUSDT", "RSIDivergenceStrategy", "15m"),
    ("DOTUSDT", "RSIDivergenceStrategy", "30m"),
    ("DOTUSDT", "RSIDivergenceStrategy", "1h"),
    ("DOTUSDT", "RSIDivergenceStrategy", "2h"),
    ("DOTUSDT", "RSIDivergenceStrategy", "4h"),
    ("DOTUSDT", "RSIDivergenceStrategy", "1d"),
    ("DOTUSDT", "MovingAverageCrossover", "15m"),
    ("DOTUSDT", "MovingAverageCrossover", "30m"),
    ("DOTUSDT", "MovingAverageCrossover", "1h"),
    ("DOTUSDT", "MovingAverageCrossover", "2h"),
    ("DOTUSDT", "MovingAverageCrossover", "4h"),
    ("DOTUSDT", "MovingAverageCrossover", "1d"),
    ("DOTUSDT", "BollingerBandStrategy", "15m"),
    ("DOTUSDT", "BollingerBandStrategy", "30m"),
    ("DOTUSDT", "BollingerBandStrategy", "1h"),
    ("DOTUSDT", "BollingerBandStrategy", "2h"),
    ("DOTUSDT", "BollingerBandStrategy", "4h"),
    ("DOTUSDT", "BollingerBandStrategy", "1d"),
    ("DOTUSDT", "MomentumStrategy", "15m"),
    ("DOTUSDT", "MomentumStrategy", "30m"),
    ("DOTUSDT", "MomentumStrategy", "1h"),
    ("DOTUSDT", "MomentumStrategy", "2h"),
    ("DOTUSDT", "MomentumStrategy", "4h"),
    ("DOTUSDT", "MomentumStrategy", "1d"),
    ("DOTUSDT", "TrendFollowingStrategy", "15m"),
    ("DOTUSDT", "TrendFollowingStrategy", "30m"),
    ("DOTUSDT", "TrendFollowingStrategy", "1h"),
    ("DOTUSDT", "TrendFollowingStrategy", "2h"),
    ("DOTUSDT", "TrendFollowingStrategy", "4h"),
    ("DOTUSDT", "TrendFollowingStrategy", "1d"),
    ("DOTUSDT", "LiveReactiveRSIStrategy", "15m"),
    ("DOTUSDT", "LiveReactiveRSIStrategy", "30m"),
    ("DOTUSDT", "LiveReactiveRSIStrategy", "1h"),
    ("DOTUSDT", "LiveReactiveRSIStrategy", "2h"),
    ("DOTUSDT", "LiveReactiveRSIStrategy", "4h"),
    ("DOTUSDT", "LiveReactiveRSIStrategy", "1d"),

    # UNIUSDT combinations
    ("UNIUSDT", "RSIStrategy", "15m"),
    ("UNIUSDT", "RSIStrategy", "30m"),
    ("UNIUSDT", "RSIStrategy", "1h"),
    ("UNIUSDT", "RSIStrategy", "2h"),
    ("UNIUSDT", "RSIStrategy", "4h"),
    ("UNIUSDT", "RSIStrategy", "1d"),
    ("UNIUSDT", "EnhancedRSIStrategy", "15m"),
    ("UNIUSDT", "EnhancedRSIStrategy", "30m"),
    ("UNIUSDT", "EnhancedRSIStrategy", "1h"),
    ("UNIUSDT", "EnhancedRSIStrategy", "2h"),
    ("UNIUSDT", "EnhancedRSIStrategy", "4h"),
    ("UNIUSDT", "EnhancedRSIStrategy", "1d"),
    ("UNIUSDT", "RSIDivergenceStrategy", "15m"),
    ("UNIUSDT", "RSIDivergenceStrategy", "30m"),
    ("UNIUSDT", "RSIDivergenceStrategy", "1h"),
    ("UNIUSDT", "RSIDivergenceStrategy", "2h"),
    ("UNIUSDT", "RSIDivergenceStrategy", "4h"),
    ("UNIUSDT", "RSIDivergenceStrategy", "1d"),
    ("UNIUSDT", "MovingAverageCrossover", "15m"),
    ("UNIUSDT", "MovingAverageCrossover", "30m"),
    ("UNIUSDT", "MovingAverageCrossover", "1h"),
    ("UNIUSDT", "MovingAverageCrossover", "2h"),
    ("UNIUSDT", "MovingAverageCrossover", "4h"),
    ("UNIUSDT", "MovingAverageCrossover", "1d"),
    ("UNIUSDT", "BollingerBandStrategy", "15m"),
    ("UNIUSDT", "BollingerBandStrategy", "30m"),
    ("UNIUSDT", "BollingerBandStrategy", "1h"),
    ("UNIUSDT", "BollingerBandStrategy", "2h"),
    ("UNIUSDT", "BollingerBandStrategy", "4h"),
    ("UNIUSDT", "BollingerBandStrategy", "1d"),
    ("UNIUSDT", "MomentumStrategy", "15m"),
    ("UNIUSDT", "MomentumStrategy", "30m"),
    ("UNIUSDT", "MomentumStrategy", "1h"),
    ("UNIUSDT", "MomentumStrategy", "2h"),
    ("UNIUSDT", "MomentumStrategy", "4h"),
    ("UNIUSDT", "MomentumStrategy", "1d"),
    ("UNIUSDT", "TrendFollowingStrategy", "15m"),
    ("UNIUSDT", "TrendFollowingStrategy", "30m"),
    ("UNIUSDT", "TrendFollowingStrategy", "1h"),
    ("UNIUSDT", "TrendFollowingStrategy", "2h"),
    ("UNIUSDT", "TrendFollowingStrategy", "4h"),
    ("UNIUSDT", "TrendFollowingStrategy", "1d"),
    ("UNIUSDT", "LiveReactiveRSIStrategy", "15m"),
    ("UNIUSDT", "LiveReactiveRSIStrategy", "30m"),
    ("UNIUSDT", "LiveReactiveRSIStrategy", "1h"),
    ("UNIUSDT", "LiveReactiveRSIStrategy", "2h"),
    ("UNIUSDT", "LiveReactiveRSIStrategy", "4h"),
    ("UNIUSDT", "LiveReactiveRSIStrategy", "1d"),

    # LINKUSDT combinations
    ("LINKUSDT", "RSIStrategy", "15m"),
    ("LINKUSDT", "RSIStrategy", "30m"),
    ("LINKUSDT", "RSIStrategy", "1h"),
    ("LINKUSDT", "RSIStrategy", "2h"),
    ("LINKUSDT", "RSIStrategy", "4h"),
    ("LINKUSDT", "RSIStrategy", "1d"),
    ("LINKUSDT", "EnhancedRSIStrategy", "15m"),
    ("LINKUSDT", "EnhancedRSIStrategy", "30m"),
    ("LINKUSDT", "EnhancedRSIStrategy", "1h"),
    ("LINKUSDT", "EnhancedRSIStrategy", "2h"),
    ("LINKUSDT", "EnhancedRSIStrategy", "4h"),
    ("LINKUSDT", "EnhancedRSIStrategy", "1d"),
    ("LINKUSDT", "RSIDivergenceStrategy", "15m"),
    ("LINKUSDT", "RSIDivergenceStrategy", "30m"),
    ("LINKUSDT", "RSIDivergenceStrategy", "1h"),
    ("LINKUSDT", "RSIDivergenceStrategy", "2h"),
    ("LINKUSDT", "RSIDivergenceStrategy", "4h"),
    ("LINKUSDT", "RSIDivergenceStrategy", "1d"),
    ("LINKUSDT", "MovingAverageCrossover", "15m"),
    ("LINKUSDT", "MovingAverageCrossover", "30m"),
    ("LINKUSDT", "MovingAverageCrossover", "1h"),
    ("LINKUSDT", "MovingAverageCrossover", "2h"),
    ("LINKUSDT", "MovingAverageCrossover", "4h"),
    ("LINKUSDT", "MovingAverageCrossover", "1d"),
    ("LINKUSDT", "BollingerBandStrategy", "15m"),
    ("LINKUSDT", "BollingerBandStrategy", "30m"),
    ("LINKUSDT", "BollingerBandStrategy", "1h"),
    ("LINKUSDT", "BollingerBandStrategy", "2h"),
    ("LINKUSDT", "BollingerBandStrategy", "4h"),
    ("LINKUSDT", "BollingerBandStrategy", "1d"),
    ("LINKUSDT", "MomentumStrategy", "15m"),
    ("LINKUSDT", "MomentumStrategy", "30m"),
    ("LINKUSDT", "MomentumStrategy", "1h"),
    ("LINKUSDT", "MomentumStrategy", "2h"),
    ("LINKUSDT", "MomentumStrategy", "4h"),
    ("LINKUSDT", "MomentumStrategy", "1d"),
    ("LINKUSDT", "TrendFollowingStrategy", "15m"),
    ("LINKUSDT", "TrendFollowingStrategy", "30m"),
    ("LINKUSDT", "TrendFollowingStrategy", "1h"),
    ("LINKUSDT", "TrendFollowingStrategy", "2h"),
    ("LINKUSDT", "TrendFollowingStrategy", "4h"),
    ("LINKUSDT", "TrendFollowingStrategy", "1d"),
    ("LINKUSDT", "LiveReactiveRSIStrategy", "15m"),
    ("LINKUSDT", "LiveReactiveRSIStrategy", "30m"),
    ("LINKUSDT", "LiveReactiveRSIStrategy", "1h"),
    ("LINKUSDT", "LiveReactiveRSIStrategy", "2h"),
    ("LINKUSDT", "LiveReactiveRSIStrategy", "4h"),
    ("LINKUSDT", "LiveReactiveRSIStrategy", "1d"),

    # SOLUSDT combinations
    ("SOLUSDT", "RSIStrategy", "15m"),
    ("SOLUSDT", "RSIStrategy", "30m"),
    ("SOLUSDT", "RSIStrategy", "1h"),
    ("SOLUSDT", "RSIStrategy", "2h"),
    ("SOLUSDT", "RSIStrategy", "4h"),
    ("SOLUSDT", "RSIStrategy", "1d"),
    ("SOLUSDT", "EnhancedRSIStrategy", "15m"),
    ("SOLUSDT", "EnhancedRSIStrategy", "30m"),
    ("SOLUSDT", "EnhancedRSIStrategy", "1h"),
    ("SOLUSDT", "EnhancedRSIStrategy", "2h"),
    ("SOLUSDT", "EnhancedRSIStrategy", "4h"),
    ("SOLUSDT", "EnhancedRSIStrategy", "1d"),
    ("SOLUSDT", "RSIDivergenceStrategy", "15m"),
    ("SOLUSDT", "RSIDivergenceStrategy", "30m"),
    ("SOLUSDT", "RSIDivergenceStrategy", "1h"),
    ("SOLUSDT", "RSIDivergenceStrategy", "2h"),
    ("SOLUSDT", "RSIDivergenceStrategy", "4h"),
    ("SOLUSDT", "RSIDivergenceStrategy", "1d"),
    ("SOLUSDT", "MovingAverageCrossover", "15m"),
    ("SOLUSDT", "MovingAverageCrossover", "30m"),
    ("SOLUSDT", "MovingAverageCrossover", "1h"),
    ("SOLUSDT", "MovingAverageCrossover", "2h"),
    ("SOLUSDT", "MovingAverageCrossover", "4h"),
    ("SOLUSDT", "MovingAverageCrossover", "1d"),
    ("SOLUSDT", "BollingerBandStrategy", "15m"),
    ("SOLUSDT", "BollingerBandStrategy", "30m"),
    ("SOLUSDT", "BollingerBandStrategy", "1h"),
    ("SOLUSDT", "BollingerBandStrategy", "2h"),
    ("SOLUSDT", "BollingerBandStrategy", "4h"),
    ("SOLUSDT", "BollingerBandStrategy", "1d"),
    ("SOLUSDT", "MomentumStrategy", "15m"),
    ("SOLUSDT", "MomentumStrategy", "30m"),
    ("SOLUSDT", "MomentumStrategy", "1h"),
    ("SOLUSDT", "MomentumStrategy", "2h"),
    ("SOLUSDT", "MomentumStrategy", "4h"),
    ("SOLUSDT", "MomentumStrategy", "1d"),
    ("SOLUSDT", "TrendFollowingStrategy", "15m"),
    ("SOLUSDT", "TrendFollowingStrategy", "30m"),
    ("SOLUSDT", "TrendFollowingStrategy", "1h"),
    ("SOLUSDT", "TrendFollowingStrategy", "2h"),
    ("SOLUSDT", "TrendFollowingStrategy", "4h"),
    ("SOLUSDT", "TrendFollowingStrategy", "1d"),
    ("SOLUSDT", "LiveReactiveRSIStrategy", "15m"),
    ("SOLUSDT", "LiveReactiveRSIStrategy", "30m"),
    ("SOLUSDT", "LiveReactiveRSIStrategy", "1h"),
    ("SOLUSDT", "LiveReactiveRSIStrategy", "2h"),
    ("SOLUSDT", "LiveReactiveRSIStrategy", "4h"),
    ("SOLUSDT", "LiveReactiveRSIStrategy", "1d"),
]

class Backtester:
    def __init__(self, client, trading_pairs, start_date, end_date, initial_balance=10000):
        self.client = client
        self.trading_pairs = trading_pairs
        self.start_date = start_date
        self.end_date = end_date
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades = []
        self.trades_to_upload = []
        self.open_positions = []
        self.daily_summary = []
        self.all_daily_summaries = []
        
        # Initialize strategies
        self.strategies = {
            'RSIStrategy': RSIStrategy(),
            'RSIDivergenceStrategy': RSIDivergenceStrategy(),
            'EnhancedRSIStrategy': EnhancedRSIStrategy(),
            'LiveReactiveRSIStrategy': LiveReactiveRSIStrategy(),
            'MovingAverageCrossover': MovingAverageCrossover(),
            'BollingerBandStrategy': BollingerBandStrategy(),
            'MomentumStrategy': MomentumStrategy(),
            'TrendFollowingStrategy': TrendFollowingStrategy()
        }

    def fetch_historical_data(self, symbol, timeframe):
        """Fetch historical data for a symbol and timeframe"""
        max_retries = 3
        retry_delay = 2  # seconds
        
        try:
            # Convert timeframe to Binance interval
            interval_map = {
                '15m': Client.KLINE_INTERVAL_15MINUTE,
                '30m': Client.KLINE_INTERVAL_30MINUTE,
                '1h': Client.KLINE_INTERVAL_1HOUR,
                '2h': Client.KLINE_INTERVAL_2HOUR,
                '4h': Client.KLINE_INTERVAL_4HOUR,
                '1d': Client.KLINE_INTERVAL_1DAY
            }
            interval = interval_map.get(timeframe)
            if not interval:
                logger.error(f"Invalid timeframe: {timeframe}")
                return None

            # Calculate chunk size based on timeframe
            chunk_days = {
                '15m': 1,    # 1 day chunks for 15m
                '30m': 2,    # 2 day chunks for 30m
                '1h': 3,     # 3 day chunks for 1h
                '2h': 5,     # 5 day chunks for 2h
                '4h': 7,     # 7 day chunks for 4h
                '1d': 30     # 30 day chunks for 1d
            }
            chunk_size = timedelta(days=chunk_days.get(timeframe, 1))

            # Initialize empty list for all klines
            all_klines = []
            current_end = self.end_date
            current_start = current_end - chunk_size

            while current_start >= self.start_date:
                # Convert to milliseconds
                start_ms = int(current_start.timestamp() * 1000)
                end_ms = int(current_end.timestamp() * 1000)

                logger.info(f"Fetching data for {symbol} at {timeframe} from {current_start} to {current_end}")

                # Retry logic for each chunk
                for retry in range(max_retries):
                    try:
                        # Fetch klines data for this chunk
                        klines = self.client.get_historical_klines(
                            symbol=symbol,
                            interval=interval,
                            start_str=start_ms,
                            end_str=end_ms
                        )
                        
                        if klines:
                            all_klines.extend(klines)
                            logger.info(f"Fetched {len(klines)} candles for {symbol} at {timeframe}")
                            break  # Success, exit retry loop
                        
                        # If no data but no error, wait and retry
                        if retry < max_retries - 1:
                            logger.warning(f"No data returned for {symbol} at {timeframe}, retrying...")
                            time.sleep(retry_delay * (retry + 1))  # Exponential backoff
                    
                    except Exception as e:
                        if retry < max_retries - 1:
                            logger.warning(f"Error fetching chunk for {symbol} at {timeframe} (attempt {retry + 1}/{max_retries}): {str(e)}")
                            time.sleep(retry_delay * (retry + 1))  # Exponential backoff
                        else:
                            logger.error(f"Failed to fetch chunk for {symbol} at {timeframe} after {max_retries} attempts: {str(e)}")
                            break
                
                # Move to next chunk
                current_end = current_start
                current_start = current_end - chunk_size
                
                # Add a delay between chunks to avoid rate limits
                time.sleep(1)  # Increased delay between chunks

            if not all_klines:
                logger.warning(f"No data returned for {symbol} at {timeframe}")
                return None

            # Create DataFrame
            df = pd.DataFrame(all_klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'trades',
                'taker_buy_base', 'taker_buy_quote', 'ignored'
            ])

            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Set timestamp as index and sort
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)

            # Remove duplicates
            df = df[~df.index.duplicated(keep='first')]

            # Validate data
            if len(df) < 100:  # Minimum required candles
                logger.warning(f"Insufficient data for {symbol} at {timeframe}: only {len(df)} candles")
                return None

            # Check for missing values
            missing_values = df[['open', 'high', 'low', 'close', 'volume']].isnull().sum()
            if missing_values.any():
                logger.warning(f"Missing values in data for {symbol} at {timeframe}: {missing_values}")
                df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])

            # Prepare data with indicators
            df = prepare_data(df)

            logger.info(f"Successfully fetched and processed {len(df)} candles for {symbol} at {timeframe}")
            return df

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol} at {timeframe}: {str(e)}")
            return None

    def run_backtest(self):
        """Run backtest for all combinations with optimized batch processing"""
        start_time = time.time()
        self.all_daily_summaries = []
        all_trades = []
        self.trades_to_upload = []
        total_trades_uploaded = 0
        
        # Get all unique dates across all combinations
        all_dates = set()
        
        # Define all time periods
        all_periods = ['15m', '30m', '1h', '2h', '4h', '1d']
        
        # Create a dictionary to store data for each symbol and timeframe
        symbol_data = {}
        
        # First pass: Collect data for all timeframes (keeping existing logic)
        logger.info("Collecting historical data...")
        for symbol in {s for s, _, _ in self.trading_pairs}:
            symbol_data[symbol] = {}
            for period in all_periods:
                try:
                    data = self.fetch_historical_data(symbol, period)
                    if data is None:
                        logger.warning(f"No data available for {symbol} at {period} timeframe")
                        continue
                    
                    if isinstance(data, pd.DataFrame) and not data.empty:
                        symbol_data[symbol][period] = data
                        all_dates.update(data.index.date)
                        logger.info(f"Successfully fetched data for {symbol} at {period} timeframe")
                    else:
                        logger.warning(f"Empty or invalid data for {symbol} at {period} timeframe")
                except Exception as e:
                    logger.error(f"Error fetching data for {symbol} at {period}: {str(e)}")
                    continue
        
        # Initialize database
        db = TradingDatabase()
        
        # Clear existing trades before starting
        logger.info("Clearing existing trades...")
        db.clear_trades()
        
        # Process each combination with progress bar
        total_combinations = len(self.trading_pairs)
        logger.info(f"Processing {total_combinations} combinations...")
        
        with tqdm(total=total_combinations, desc="Processing combinations") as pbar:
            for symbol, strategy_name, timeframe in self.trading_pairs:
                try:
                    # Reset for new combination
                    self.balance = self.initial_balance
                    self.trades = []
                    self.open_positions = []
                    self.daily_summary = []
                    
                    # Get the data for this symbol and timeframe
                    raw_data = symbol_data.get(symbol, {}).get(timeframe)
                    
                    if raw_data is None:
                        logger.warning(f"No data available for {symbol} using {strategy_name} at {timeframe}")
                        pbar.update(1)
                        continue
                    
                    # Process the combination
                    self._process_combination(symbol, strategy_name, timeframe, raw_data.copy(), db)
                    
                    # Add trades to all_trades list
                    all_trades.extend(self.trades)
                    
                    # Upload any remaining trades for this combination
                    if self.trades_to_upload:
                        logger.info(f"Uploading final batch of {len(self.trades_to_upload)} trades for {symbol} {strategy_name}")
                        db.batch_upload_trades(self.trades_to_upload, collection_name="trades_backTestBot")
                        total_trades_uploaded += len(self.trades_to_upload)
                        self.trades_to_upload = []
                    
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"Error processing combination {symbol} {strategy_name} {timeframe}: {str(e)}")
                    pbar.update(1)
                    continue
        
        # Export results
        self._export_results(all_trades)
        
        end_time = time.time()
        logger.info(f"Backtest completed in {end_time - start_time:.2f} seconds")
        
        # Print summary statistics
        logger.info("\n=== BACKTEST SUMMARY ===")
        logger.info(f"Total combinations processed: {total_combinations}")
        logger.info(f"Total trades placed: {len(all_trades)}")
        logger.info(f"Total trades uploaded to Firestore: {total_trades_uploaded + len(self.trades_to_upload)}")
        
        # Count trades by strategy
        strategy_counts = {}
        for trade in all_trades:
            strategy = trade['strategy']
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        logger.info("\nTrades by strategy:")
        for strategy, count in strategy_counts.items():
            logger.info(f"{strategy}: {count} trades")
        
        # Calculate total profit
        total_profit = sum(trade['profit'] for trade in all_trades)
        logger.info(f"\nTotal profit: ${total_profit:.2f}")
        logger.info("=====================\n")

    def _process_combination(self, symbol, strategy_name, timeframe, data, db):
        """Process a single combination of symbol, strategy, and timeframe"""
        strategy = self.strategies.get(strategy_name)
        if strategy is None:
            logger.error(f"Unknown strategy: {strategy_name}")
            return
        
        if hasattr(strategy, 'set_timeframe'):
            strategy.set_timeframe(timeframe)
        
        signals = strategy.generate_signals(data)
        if signals is None:
            logger.warning(f"No signals generated for {symbol} at {timeframe}")
            return
        
        # Process signals
        for idx, row in data.iterrows():
            current_date = idx.date() if hasattr(idx, 'date') else pd.to_datetime(idx).date()
            
            if idx in signals.index:
                signal = signals.loc[idx]
                if signal['position'] != 0:
                    self._process_signal(symbol, strategy_name, timeframe, row, idx, signal)
            
            # Update open positions
            if self.open_positions:
                self._update_positions(row, idx, db)

    def _process_signal(self, symbol, strategy_name, timeframe, row, idx, signal):
        """Process a trading signal"""
        position_size = calculate_position_size(
            row['close'],
            symbol,
            self.balance,
            0.05
        )
        
        trade = execute_trade(
            symbol,
            'LONG' if signal['position'] > 0 else 'SHORT',
            row['close'],
            idx,
            strategy_name,
            position_size,
            timeframe,
            0.02,
            0.06
        )
        
        self.open_positions.append(trade)
        logger.info(f"Added trade to open positions. Total open positions: {len(self.open_positions)}")

    def _update_positions(self, row, idx, db):
        """Update open positions and handle closed trades"""
        closed_positions = update_open_positions(
            self.open_positions,
            row['close'],
            idx,
            0.02,
            0.06
        )
        
        for closed_trade in closed_positions:
            closed_trade['profit'] = calculate_fee_adjusted_profit(closed_trade)
            self.balance += closed_trade['profit']
            self.trades.append(closed_trade)
            
            trade_data = {
                'entry_time': closed_trade['entry_time'],
                'exit_time': closed_trade['exit_time'],
                'strategy': closed_trade['strategy'],
                'symbol': closed_trade['symbol'],
                'timeframe': closed_trade['timeframe'],
                'trade_type': closed_trade['type'],
                'entry_price': closed_trade['entry_price'],
                'position_size': closed_trade['position_size'],
                'stop_loss': closed_trade['stop_loss'],
                'take_profit': closed_trade['take_profit'],
                'profit': closed_trade['profit'],
                'fees': closed_trade.get('fees', 0)
            }
            
            self.trades_to_upload.append(trade_data)
            
            if len(self.trades_to_upload) >= 500:
                logger.info(f"Uploading batch of {len(self.trades_to_upload)} trades")
                db.batch_upload_trades(self.trades_to_upload, collection_name="trades_backTestBot")
                total_trades_uploaded += len(self.trades_to_upload)
                self.trades_to_upload = []

    def _export_results(self, all_trades):
        """Export backtest results"""
        if all_trades:
            logger.info(f"Number of trades collected: {len(all_trades)}")
            export_aggregated_summary_to_csv(all_trades, 'output/summary_report_aggregated.csv')
            
            trades_df = pd.DataFrame(all_trades)
            trades_df.to_csv('output/all_trades.csv', index=False)
            logger.info("Exported all trades to 'output/all_trades.csv'")
            
            # Upload any remaining trades to Firestore
            if self.trades_to_upload:
                logger.info(f"Uploading final batch of {len(self.trades_to_upload)} trades")
                db = TradingDatabase()
                db.batch_upload_trades(self.trades_to_upload, collection_name="trades_backTestBot")
                self.trades_to_upload = []
        else:
            logger.error("No trades were collected during backtest")

def main():
    # Initialize Binance client
    client = Client(API_KEY, API_SECRET, testnet=TESTNET)
    
    # Create output directories if they don't exist
    os.makedirs('data/output', exist_ok=True)
    os.makedirs('output', exist_ok=True)  # Ensure output directory exists
    
    # Set date range for backtest (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Create backtester instance with specific date range
    backtester = Backtester(
        client=client,
        trading_pairs=BACKTEST_COMBOS,
        start_date=start_date,
        end_date=end_date,
        initial_balance=INITIAL_BALANCE
    )
    
    # Run backtest
    backtester.run_backtest()
    
    # Generate performance graphs
    subprocess.run([sys.executable, 'utils/create_performance_graphs.py'], check=True)
    
    # Upload results to Google Sheets and capture the output
    sheets_result = subprocess.run(
        [sys.executable, 'utils/upload_to_sheets.py'],
        capture_output=True,
        text=True,
        check=False
    )
    
    # Print Google Sheets upload status
    print("\n=== GOOGLE SHEETS UPLOAD STATUS ===")
    if sheets_result.returncode == 0:
        print(sheets_result.stdout.strip())
    else:
        print("✗ Failed to upload to Google Sheets")
        print("Error details:")
        print(sheets_result.stderr.strip())
    print("===================================\n")
    
    # Verify files were created
    logger.info("Checking output files:")
    for file in ['summary_report_daily.csv', 'summary_report_overall.csv', 'summary_report_aggregated.csv']:
        if os.path.exists(f'output/{file}'):
            logger.info(f"✓ {file} was created successfully")
        else:
            logger.error(f"✗ {file} was not created")

if __name__ == "__main__":
    main() 