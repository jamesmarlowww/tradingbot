from utils.bigquery_database import BigQueryDatabase

db = BigQueryDatabase()
trades = db.get_trades(limit=10)

print("Recent trades in BigQuery:")
print("=" * 50)
for i, trade in enumerate(trades, 1):
    print(f"{i}. Run: {trade.get('run_name', 'N/A')}")
    print(f"   Strategy: {trade.get('strategy', 'N/A')}")
    print(f"   Symbol: {trade.get('symbol', 'N/A')}")
    print(f"   Entry: {trade.get('entry_time', 'N/A')}")
    print(f"   Exit: {trade.get('exit_time', 'N/A')}")
    print(f"   Profit: ${trade.get('profit', 0):.2f}")
    print("-" * 30)

# Also check unique run_names
all_trades = db.get_trades(limit=None)
run_names = set(trade.get('run_name', 'N/A') for trade in all_trades)
print(f"\nUnique run_names in BigQuery: {run_names}")
print(f"Total trades in BigQuery: {len(all_trades)}") 