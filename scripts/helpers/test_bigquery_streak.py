"""
Test script to verify BigQuery streak analysis integration
"""
import os
import sys
from datetime import datetime, timedelta

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from utils.bigquery_database import BigQueryDatabase
from config.automation_config import *

def test_bigquery_streak_analysis():
    """Test the BigQuery streak analysis functionality"""
    print("=== BIGQUERY STREAK ANALYSIS TEST ===\n")
    
    try:
        db = BigQueryDatabase()
        
        # Test 1: Check if we can connect to BigQuery
        print("1. Testing BigQuery connection...")
        stats = db.get_database_stats()
        print(f"   ✅ Connected to BigQuery")
        print(f"   Total trades in database: {stats.get('total_trades', 'Unknown')}")
        
        # Test 2: Get recent test bot trades
        print("\n2. Getting recent test bot trades...")
        filters = {
            'run_name': 'testBot',
            'limit': 10
        }
        trades = db.get_trades(filters=filters)
        print(f"   Found {len(trades)} recent test bot trades")
        
        if trades:
            print("   Recent trades:")
            for trade in trades[:3]:  # Show first 3
                print(f"     {trade.get('entry_time', 'N/A')} - {trade.get('symbol', 'N/A')} - ${trade.get('profit', 0):.2f}")
        
        # Test 3: Calculate daily profits for last 7 days
        print("\n3. Calculating daily profits for last 7 days...")
        today = datetime.now().date()
        daily_profits = []
        
        for i in range(7):
            check_date = today - timedelta(days=i+1)
            start_datetime = datetime.combine(check_date, datetime.min.time())
            end_datetime = datetime.combine(check_date, datetime.max.time())
            
            filters = {
                'start_date': start_datetime,
                'end_date': end_datetime,
                'run_name': 'testBot'
            }
            
            day_trades = db.get_trades(filters=filters, limit=None)
            daily_profit = sum(trade.get('profit', 0.0) for trade in day_trades)
            daily_profits.append(daily_profit)
            
            status = "✅ POSITIVE" if daily_profit > MIN_PROFIT_THRESHOLD else "❌ NEGATIVE"
            print(f"   {check_date}: ${daily_profit:.2f} - {status} ({len(day_trades)} trades)")
        
        # Test 4: Check streak conditions
        print(f"\n4. Streak analysis (last {REQUIRED_POSITIVE_DAYS} days)...")
        recent_profits = daily_profits[:REQUIRED_POSITIVE_DAYS]
        positive_days = sum(1 for profit in recent_profits if profit > MIN_PROFIT_THRESHOLD)
        
        print(f"   Positive days: {positive_days}/{REQUIRED_POSITIVE_DAYS}")
        print(f"   Required days: {REQUIRED_POSITIVE_DAYS}")
        print(f"   Min profit threshold: ${MIN_PROFIT_THRESHOLD}")
        
        should_enable = positive_days >= REQUIRED_POSITIVE_DAYS
        print(f"   Result: {'🟢 TRADING ENABLED' if should_enable else '🔴 TRADING DISABLED'}")
        
        # Test 5: Compare with your SQL analysis
        print(f"\n5. Comparing with your SQL analysis...")
        print(f"   Your data showed 5-day positive combinations with +$489.38 net profit")
        print(f"   This suggests 5-day streaks are profitable")
        print(f"   Current automation requires {REQUIRED_POSITIVE_DAYS} positive days")
        
        if should_enable:
            print(f"   ✅ Current system would enable trading based on recent performance")
        else:
            print(f"   ⚠️  Current system would disable trading - may need more data")
        
        # Test 6: Show configuration
        print(f"\n6. Current automation configuration:")
        print(f"   STREAK_AUTOMATION_ENABLED: {STREAK_AUTOMATION_ENABLED}")
        print(f"   REQUIRED_POSITIVE_DAYS: {REQUIRED_POSITIVE_DAYS}")
        print(f"   MIN_PROFIT_THRESHOLD: ${MIN_PROFIT_THRESHOLD}")
        print(f"   EMERGENCY_OVERRIDE: {EMERGENCY_OVERRIDE}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

def test_sample_data_upload():
    """Test uploading sample data to BigQuery"""
    print("\n=== SAMPLE DATA UPLOAD TEST ===")
    
    try:
        db = BigQueryDatabase()
        
        # Create sample trade data
        sample_trades = []
        today = datetime.now()
        
        # Create 5 days of positive trades
        for i in range(5):
            trade_date = today - timedelta(days=i+1)
            sample_trade = {
                'entry_time': trade_date.replace(hour=10, minute=0, second=0, microsecond=0),
                'exit_time': trade_date.replace(hour=14, minute=0, second=0, microsecond=0),
                'strategy': 'EnhancedRSIStrategy',
                'symbol': 'ETHUSDT',
                'timeframe': '4h',
                'trade_type': 'LONG',
                'entry_price': 2000.0 + i * 10,
                'exit_price': 2020.0 + i * 10,
                'position_size': 0.1,
                'profit': 20.0 + i * 5,  # Positive profit
                'fees': 0.4,
                'run_name': 'testBot'
            }
            sample_trades.append(sample_trade)
        
        print(f"Created {len(sample_trades)} sample trades")
        
        # Upload to BigQuery
        uploaded_count = db.batch_upload_trades(sample_trades)
        print(f"Uploaded {uploaded_count} sample trades to BigQuery")
        
        # Verify upload
        filters = {'run_name': 'testBot', 'limit': 5}
        recent_trades = db.get_trades(filters=filters)
        print(f"Verified {len(recent_trades)} trades in database")
        
    except Exception as e:
        print(f"❌ Error uploading sample data: {e}")

if __name__ == "__main__":
    test_bigquery_streak_analysis()
    
    # Uncomment to test sample data upload
    # test_sample_data_upload() 