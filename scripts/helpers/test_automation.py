"""
Test script for streak-based automation logic
"""
import os
import sys
from datetime import datetime, timedelta
import json

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from config.automation_config import *

def create_sample_trade_history():
    """Create sample trade history for testing"""
    today = datetime.now().date()
    
    # Create sample trades for the last 7 days
    sample_trades = []
    
    # Day 1: +$50 profit
    sample_trades.append({
        'symbol': 'ETHUSDT',
        'strategy': 'EnhancedRSIStrategy',
        'entry_time': int((today - timedelta(days=1)).timestamp() * 1000),
        'close_time': int((today - timedelta(days=1)).timestamp() * 1000),
        'profit_usd': 50.0
    })
    
    # Day 2: +$30 profit
    sample_trades.append({
        'symbol': 'SOLUSDT',
        'strategy': 'TrendFollowingStrategy',
        'entry_time': int((today - timedelta(days=2)).timestamp() * 1000),
        'close_time': int((today - timedelta(days=2)).timestamp() * 1000),
        'profit_usd': 30.0
    })
    
    # Day 3: +$20 profit
    sample_trades.append({
        'symbol': 'LINKUSDT',
        'strategy': 'EnhancedRSIStrategy',
        'entry_time': int((today - timedelta(days=3)).timestamp() * 1000),
        'close_time': int((today - timedelta(days=3)).timestamp() * 1000),
        'profit_usd': 20.0
    })
    
    # Day 4: +$40 profit
    sample_trades.append({
        'symbol': 'ETHUSDT',
        'strategy': 'EnhancedRSIStrategy',
        'entry_time': int((today - timedelta(days=4)).timestamp() * 1000),
        'close_time': int((today - timedelta(days=4)).timestamp() * 1000),
        'profit_usd': 40.0
    })
    
    # Day 5: +$25 profit
    sample_trades.append({
        'symbol': 'SOLUSDT',
        'strategy': 'TrendFollowingStrategy',
        'entry_time': int((today - timedelta(days=5)).timestamp() * 1000),
        'close_time': int((today - timedelta(days=5)).timestamp() * 1000),
        'profit_usd': 25.0
    })
    
    # Day 6: -$10 loss (breaking the streak)
    sample_trades.append({
        'symbol': 'LINKUSDT',
        'strategy': 'EnhancedRSIStrategy',
        'entry_time': int((today - timedelta(days=6)).timestamp() * 1000),
        'close_time': int((today - timedelta(days=6)).timestamp() * 1000),
        'profit_usd': -10.0
    })
    
    # Day 7: +$15 profit
    sample_trades.append({
        'symbol': 'ETHUSDT',
        'strategy': 'EnhancedRSIStrategy',
        'entry_time': int((today - timedelta(days=7)).timestamp() * 1000),
        'close_time': int((today - timedelta(days=7)).timestamp() * 1000),
        'profit_usd': 15.0
    })
    
    return sample_trades

def calculate_daily_profit_test(trades, date):
    """Calculate total profit for a specific date (test version)"""
    total_profit = 0.0
    
    for trade in trades:
        trade_date = datetime.fromtimestamp(trade['close_time'] / 1000).date()
        if trade_date == date:
            profit = trade.get('profit_usd', 0.0)
            total_profit += profit
    
    return total_profit

def test_streak_logic():
    """Test the streak-based automation logic"""
    print("=== STREAK-BASED AUTOMATION TEST ===\n")
    
    # Load configuration
    print(f"Configuration:")
    print(f"  STREAK_AUTOMATION_ENABLED: {STREAK_AUTOMATION_ENABLED}")
    print(f"  REQUIRED_POSITIVE_DAYS: {REQUIRED_POSITIVE_DAYS}")
    print(f"  MIN_PROFIT_THRESHOLD: ${MIN_PROFIT_THRESHOLD}")
    print(f"  EMERGENCY_OVERRIDE: {EMERGENCY_OVERRIDE}")
    print()
    
    # Create sample trade history
    sample_trades = create_sample_trade_history()
    
    # Calculate daily profits for the last 5 days
    today = datetime.now().date()
    daily_profits = []
    
    print("Daily Profit Analysis:")
    print("-" * 40)
    
    for i in range(REQUIRED_POSITIVE_DAYS):
        check_date = today - timedelta(days=i+1)
        daily_profit = calculate_daily_profit_test(sample_trades, check_date)
        daily_profits.append(daily_profit)
        
        status = "✅ POSITIVE" if daily_profit > MIN_PROFIT_THRESHOLD else "❌ NEGATIVE"
        print(f"  {check_date}: ${daily_profit:.2f} - {status}")
    
    # Check if we have required consecutive positive days
    positive_days = sum(1 for profit in daily_profits if profit > MIN_PROFIT_THRESHOLD)
    
    print(f"\nStreak Analysis:")
    print(f"  Positive days: {positive_days}/{REQUIRED_POSITIVE_DAYS}")
    print(f"  Required days: {REQUIRED_POSITIVE_DAYS}")
    
    # Determine if trading should be enabled
    should_enable = positive_days >= REQUIRED_POSITIVE_DAYS
    
    print(f"\nResult:")
    if should_enable:
        print("  🟢 TRADING WOULD BE ENABLED")
    else:
        print("  🔴 TRADING WOULD BE DISABLED")
    
    print(f"\nReasoning:")
    if positive_days >= REQUIRED_POSITIVE_DAYS:
        print(f"  ✅ {positive_days} consecutive positive days meets the {REQUIRED_POSITIVE_DAYS} day requirement")
    else:
        print(f"  ❌ Only {positive_days} positive days, need {REQUIRED_POSITIVE_DAYS}")
    
    # Test different scenarios
    print(f"\n=== SCENARIO TESTING ===")
    
    # Scenario 1: All 5 days positive
    print(f"\nScenario 1: All 5 days positive")
    all_positive = [50.0, 30.0, 20.0, 40.0, 25.0]
    positive_count = sum(1 for profit in all_positive if profit > MIN_PROFIT_THRESHOLD)
    print(f"  Result: {'🟢 ENABLED' if positive_count >= REQUIRED_POSITIVE_DAYS else '🔴 DISABLED'}")
    
    # Scenario 2: 4 days positive, 1 negative
    print(f"\nScenario 2: 4 days positive, 1 negative")
    mixed_days = [50.0, 30.0, 20.0, 40.0, -10.0]
    positive_count = sum(1 for profit in mixed_days if profit > MIN_PROFIT_THRESHOLD)
    print(f"  Result: {'🟢 ENABLED' if positive_count >= REQUIRED_POSITIVE_DAYS else '🔴 DISABLED'}")
    
    # Scenario 3: All days negative
    print(f"\nScenario 3: All days negative")
    all_negative = [-10.0, -20.0, -15.0, -25.0, -30.0]
    positive_count = sum(1 for profit in all_negative if profit > MIN_PROFIT_THRESHOLD)
    print(f"  Result: {'🟢 ENABLED' if positive_count >= REQUIRED_POSITIVE_DAYS else '🔴 DISABLED'}")

if __name__ == "__main__":
    test_streak_logic() 