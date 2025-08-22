#!/usr/bin/env python3
"""
Check BigQuery data and compare with expectations
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_database import BigQueryDatabase
import pandas as pd
from tabulate import tabulate

def check_bigquery_data():
    """Check what's in BigQuery"""
    try:
        db = BigQueryDatabase()
        
        # Get all trades (with high limit to get all)
        trades = db.get_trades(limit=10000)
        trades_list = trades
        
        print(f"Total trades in BigQuery: {len(trades_list)}")
        
        if len(trades_list) > 0:
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(trades_list)
            
            print("\n=== BIGQUERY DATA SUMMARY ===")
            print(f"Date range: {df['entry_time'].min()} to {df['entry_time'].max()}")
            print(f"Symbols: {df['symbol'].unique()}")
            print(f"Strategies: {df['strategy'].unique()}")
            print(f"Timeframes: {df['timeframe'].unique()}")
            print(f"Run names: {df['run_name'].unique()}")
            
            print("\n=== TRADES BY STRATEGY ===")
            strategy_counts = df['strategy'].value_counts()
            print(tabulate(strategy_counts.reset_index(), headers=['Strategy', 'Count'], tablefmt='grid'))
            
            print("\n=== TRADES BY SYMBOL ===")
            symbol_counts = df['symbol'].value_counts()
            print(tabulate(symbol_counts.reset_index(), headers=['Symbol', 'Count'], tablefmt='grid'))
            
            print("\n=== SAMPLE TRADES ===")
            sample_trades = df.head(10)[['entry_time', 'symbol', 'strategy', 'timeframe', 'trade_type', 'entry_price', 'profit', 'run_name']]
            print(tabulate(sample_trades, headers='keys', tablefmt='grid', showindex=False))
            
            # Check for any trades with run_name = 'backTestBot'
            backtest_trades = df[df['run_name'] == 'backTestBot']
            print(f"\nTrades with run_name 'backTestBot': {len(backtest_trades)}")
            
        else:
            print("No trades found in BigQuery")
            
    except Exception as e:
        print(f"Error checking BigQuery data: {e}")

if __name__ == "__main__":
    check_bigquery_data() 