from utils.bigquery_database import BigQueryDatabase
from datetime import datetime, timedelta
import pandas as pd

def check_streak_status():
    """Check current streak status from BigQuery data"""
    db = BigQueryDatabase()
    
    # Get all trades from the last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    filters = {
        'start_date': start_date,
        'end_date': end_date
    }
    
    trades = db.get_trades(filters=filters, limit=None)
    print(f"Found {len(trades)} trades in the last 30 days")
    
    if not trades:
        print("No trades found in the last 30 days")
        return
    
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(trades)
    df['exit_time'] = pd.to_datetime(df['exit_time'])
    df['date'] = df['exit_time'].dt.date
    
    # Calculate daily profit
    daily_profit = df.groupby('date')['profit'].sum().reset_index()
    daily_profit['date'] = pd.to_datetime(daily_profit['date'])
    daily_profit = daily_profit.sort_values('date')
    
    print("\n=== Daily Profit Analysis ===")
    print(f"{'Date':<12} {'Profit':<12} {'Status':<10}")
    print("-" * 35)
    
    # Check last 10 days
    recent_days = daily_profit.tail(10)
    positive_days = 0
    consecutive_positive = 0
    
    for _, row in recent_days.iterrows():
        profit = row['profit']
        status = "✅ POSITIVE" if profit > 0 else "❌ NEGATIVE"
        print(f"{row['date'].strftime('%Y-%m-%d'):<12} ${profit:<11.2f} {status:<10}")
        
        if profit > 0:
            positive_days += 1
            consecutive_positive += 1
        else:
            consecutive_positive = 0
    
    print(f"\n=== Streak Analysis ===")
    print(f"Positive days in last 10 days: {positive_days}/10")
    print(f"Current consecutive positive days: {consecutive_positive}")
    
    # Check if trading would be enabled (5-day streak)
    trading_enabled = consecutive_positive >= 5
    print(f"Trading would be: {'🟢 ENABLED' if trading_enabled else '🔴 DISABLED'}")
    
    # Show total trades by run_name
    print(f"\n=== Trades by Bot Type ===")
    run_name_counts = df['run_name'].value_counts()
    for run_name, count in run_name_counts.items():
        print(f"{run_name}: {count} trades")
    
    return trading_enabled, consecutive_positive

if __name__ == "__main__":
    check_streak_status() 