#!/usr/bin/env python3
"""
Test script to verify profit streak logic
"""

import os
import sys
from datetime import datetime, timedelta

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

from utils.bigquery_database import BigQueryDatabase

def test_profit_streak_logic():
    """Test the profit streak logic"""
    print("🧪 Testing Profit Streak Logic...")
    
    # Initialize database
    db = BigQueryDatabase()
    
    # Test getting profitable combinations
    print("\n📊 Querying profitable combinations...")
    profitable_combinations = db.get_profitable_combinations(
        run_name='monitorBot',
        streak_days=5
    )
    
    print(f"\n✅ Found {len(profitable_combinations)} combinations with 5-day profit streaks")
    
    if profitable_combinations:
        print("\n🏆 Top 10 Profitable Combinations:")
        for i, combo in enumerate(profitable_combinations[:10]):
            print(f"{i+1}. {combo['combination']} - Net Profit: ${combo['net_profit_after_fees']:.2f}")
            print(f"   Last 5 days: ${combo['np_day_1_ago']:.2f}, ${combo['np_day_2_ago']:.2f}, ${combo['np_day_3_ago']:.2f}, ${combo['np_day_4_ago']:.2f}, ${combo['np_day_5_ago']:.2f}")
    else:
        print("\n❌ No combinations with 5-day profit streaks found")
        print("   This is normal if monitorBot hasn't been running long enough")
    
    # Test getting daily profits
    print("\n📈 Testing daily profits query...")
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=6)
    
    daily_profits = db.get_daily_profits(
        start_date=start_date,
        end_date=end_date,
        run_name='monitorBot'
    )
    
    print(f"📅 Daily profits for last 6 days: {len(daily_profits)} days found")
    for profit in daily_profits:
        print(f"   {profit['trade_date']}: ${profit['daily_profit']:.2f} ({profit['trade_count']} trades)")

if __name__ == "__main__":
    test_profit_streak_logic()
