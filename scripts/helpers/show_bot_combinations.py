#!/usr/bin/env python3
"""
Show Bot Combinations - Display what each bot runs
"""

import os
import sys

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from scripts.backTestBot import BACKTEST_COMBOS

def show_combinations():
    """Show all combinations organized by bot"""
    
    print("=" * 80)
    print("BOT COMBINATIONS OVERVIEW")
    print("=" * 80)
    
    # Organize by symbol
    symbols = {}
    strategies = set()
    timeframes = set()
    
    for symbol, strategy, timeframe in BACKTEST_COMBOS:
        if symbol not in symbols:
            symbols[symbol] = []
        symbols[symbol].append((strategy, timeframe))
        strategies.add(strategy)
        timeframes.add(timeframe)
    
    print(f"\n📊 TOTAL COMBINATIONS: {len(BACKTEST_COMBOS)}")
    print(f"📈 SYMBOLS: {len(symbols)}")
    print(f"🎯 STRATEGIES: {len(strategies)}")
    print(f"⏰ TIMEFRAMES: {len(timeframes)}")
    
    print(f"\n📈 SYMBOLS COVERED:")
    for symbol in sorted(symbols.keys()):
        print(f"  • {symbol} ({len(symbols[symbol])} combinations)")
    
    print(f"\n🎯 STRATEGIES COVERED:")
    for strategy in sorted(strategies):
        count = sum(1 for _, s, _ in BACKTEST_COMBOS if s == strategy)
        print(f"  • {strategy} ({count} combinations)")
    
    print(f"\n⏰ TIMEFRAMES COVERED:")
    for timeframe in sorted(timeframes, key=lambda x: {
        '15m': 1, '30m': 2, '1h': 3, '2h': 4, '4h': 5, '1d': 6
    }.get(x, 7)):
        count = sum(1 for _, _, t in BACKTEST_COMBOS if t == timeframe)
        print(f"  • {timeframe} ({count} combinations)")
    
    print(f"\n" + "=" * 80)
    print("DETAILED BREAKDOWN BY SYMBOL")
    print("=" * 80)
    
    for symbol in sorted(symbols.keys()):
        print(f"\n🔸 {symbol} ({len(symbols[symbol])} combinations):")
        
        # Group by strategy
        strategy_groups = {}
        for strategy, timeframe in symbols[symbol]:
            if strategy not in strategy_groups:
                strategy_groups[strategy] = []
            strategy_groups[strategy].append(timeframe)
        
        for strategy in sorted(strategy_groups.keys()):
            timeframes_list = sorted(strategy_groups[strategy], key=lambda x: {
                '15m': 1, '30m': 2, '1h': 3, '2h': 4, '4h': 5, '1d': 6
            }.get(x, 7))
            print(f"  • {strategy}: {', '.join(timeframes_list)}")
    
    print(f"\n" + "=" * 80)
    print("BOT USAGE")
    print("=" * 80)
    
    print(f"""
🤖 BACKTEST BOT (scripts/backTestBot.py):
   • Runs all {len(BACKTEST_COMBOS)} combinations
   • Historical backtesting only
   • Outputs to BigQuery with run_name = 'backTestBot'

📊 MONITOR BOT (scripts/monitorBot.py):
   • Uses same {len(BACKTEST_COMBOS)} combinations (imported from backTestBot)
   • Can run on different schedules (15m, 30m, 1h, 2h, 4h, daily, comprehensive)
   • Outputs to BigQuery with run_name = 'monitorBot'

🧪 TEST BOT (scripts/testTradingBot.py):
   • Uses subset of combinations (defined in testTradingBot.py)
   • Only trades when streak conditions are met
   • Outputs to BigQuery with run_name = 'testBot'

🚀 PROD BOT (scripts/prodTradingBot.py):
   • Uses subset of combinations (defined in prodTradingBot.py)
   • Only trades when conditions are met
   • Outputs to BigQuery with run_name = 'prodBot'

🎛️  SYSTEM RUNNER (scripts/run_bot_system.py):
   • Orchestrates all bots
   • Can run individual bots or all together
   • Controls based on streak conditions
""")
    
    print(f"\n" + "=" * 80)
    print("NEW STRATEGIES ADDED")
    print("=" * 80)
    
    print(f"""
✅ VWAPStrategy:
   • Volume-Weighted Average Price strategy
   • Institutional favorite
   • Simple: Buy below VWAP, sell above VWAP
   • Added to BTCUSDT and ETHUSDT (12 combinations each)

✅ PriceActionBreakoutStrategy:
   • Pure price-based breakout strategy
   • No technical indicators, just price action
   • Simple: Break above recent high = buy, break below recent low = sell
   • Added to BTCUSDT and ETHUSDT (12 combinations each)

📈 TOTAL NEW COMBINATIONS: 48 (24 per symbol)
""")

if __name__ == "__main__":
    show_combinations() 