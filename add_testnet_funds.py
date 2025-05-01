from binance.client import Client
from config import API_KEY, API_SECRET, TESTNET
import requests
import json

def add_testnet_funds():
    """Add testnet funds for all trading pairs"""
    try:
        client = Client(API_KEY, API_SECRET, testnet=TESTNET)
        
        # List of assets to fund
        assets = ['BTC', 'ETH', 'SOL', 'AVAX', 'USDT']
        
        print("Current balances:")
        for asset in assets:
            try:
                balance = client.get_asset_balance(asset=asset)
                print(f"{asset}: {balance['free']}")
            except Exception as e:
                print(f"Error getting {asset} balance: {e}")
        
        # Try multiple times for AVAX with smaller quantities
        print("\nAttempting to add AVAX in smaller increments...")
        for i in range(3):  # Try 3 times
            try:
                # Create a test buy order for AVAX with smaller quantity
                order = client.create_test_order(
                    symbol='AVAXUSDT',
                    side='BUY',
                    type='MARKET',
                    quantity=2.0  # Smaller quantity
                )
                print(f"Attempt {i+1}: Created test order for AVAXUSDT with quantity 2.0")
                
                # Check new balance
                new_balance = client.get_asset_balance(asset='AVAX')
                print(f"New AVAX balance: {new_balance['free']}")
                
            except Exception as e:
                print(f"Error creating test order for AVAX: {e}")
        
        print("\nFinal balances:")
        for asset in assets:
            try:
                balance = client.get_asset_balance(asset=asset)
                print(f"{asset}: {balance['free']}")
            except Exception as e:
                print(f"Error getting {asset} balance: {e}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_testnet_funds() 