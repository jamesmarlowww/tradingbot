"""
Compare trades in CSV, BigQuery, and self_trades.json
"""
import os
import sys
import pandas as pd
import json
from tabulate import tabulate

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from utils.bigquery_database import BigQueryDatabase

def main():
    # Load trades from CSV
    csv_file = 'output/all_trades.csv'
    if not os.path.exists(csv_file):
        print(f"CSV file not found: {csv_file}")
        df_csv = pd.DataFrame()
    else:
        df_csv = pd.read_csv(csv_file)
        print(f"Total trades in CSV: {len(df_csv)}")
        print("Sample trades from CSV:")
        print(tabulate(df_csv.head(5), headers='keys', tablefmt='psql'))

    # Load trades from self_trades.json
    self_file = 'output/self_trades.json'
    if not os.path.exists(self_file):
        print(f"self_trades.json not found: {self_file}")
        df_self = pd.DataFrame()
    else:
        with open(self_file, 'r') as f:
            self_trades = json.load(f)
        df_self = pd.DataFrame(self_trades)
        print(f"Total trades in self_trades.json: {len(df_self)}")
        print("Sample trades from self_trades.json:")
        print(tabulate(df_self.head(5), headers='keys', tablefmt='psql'))

    # Load trades from BigQuery
    db = BigQueryDatabase()
    bq_trades = db.get_trades(limit=None)  # Remove limit to get all trades
    if bq_trades:
        df_bq = pd.DataFrame(bq_trades)
        print(f"Total trades in BigQuery: {len(df_bq)}")
        print("Sample trades from BigQuery:")
        print(tabulate(df_bq.head(5), headers='keys', tablefmt='psql'))
    else:
        print("No trades found in BigQuery.")
        df_bq = pd.DataFrame()

    # Clean summary table
    print("\n=== TRADE COUNTS SUMMARY ===")
    summary = [
        ["CSV", len(df_csv)],
        ["self_trades.json", len(df_self)],
        ["BigQuery", len(df_bq)]
    ]
    print(tabulate(summary, headers=["Source", "Trade Count"], tablefmt="github"))

    # Optionally, compare a few key fields
    if not df_csv.empty and not df_bq.empty:
        csv_keys = set(tuple(row) for row in df_csv[['entry_time','symbol','strategy','entry_price']].head(20).values)
        bq_keys = set(tuple(row) for row in df_bq[['entry_time','symbol','strategy','entry_price']].head(20).values)
        overlap = csv_keys & bq_keys
        print(f"\nSample overlap in first 20 trades (by entry_time, symbol, strategy, entry_price): {len(overlap)}")
        if overlap:
            print("Example overlap:")
            for item in list(overlap)[:3]:
                print(item)
    if not df_csv.empty and not df_self.empty:
        csv_keys = set(tuple(row) for row in df_csv[['entry_time','symbol','strategy','entry_price']].head(20).values)
        self_keys = set(tuple(row) for row in df_self[['entry_time','symbol','strategy','entry_price']].head(20).values)
        overlap = csv_keys & self_keys
        print(f"\nSample overlap in first 20 trades (CSV vs self_trades.json): {len(overlap)}")
        if overlap:
            print("Example overlap:")
            for item in list(overlap)[:3]:
                print(item)
    if not df_self.empty and not df_bq.empty:
        self_keys = set(tuple(row) for row in df_self[['entry_time','symbol','strategy','entry_price']].head(20).values)
        bq_keys = set(tuple(row) for row in df_bq[['entry_time','symbol','strategy','entry_price']].head(20).values)
        overlap = self_keys & bq_keys
        print(f"\nSample overlap in first 20 trades (self_trades.json vs BigQuery): {len(overlap)}")
        if overlap:
            print("Example overlap:")
            for item in list(overlap)[:3]:
                print(item)

if __name__ == "__main__":
    main() 