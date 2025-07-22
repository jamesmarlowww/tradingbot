import os
import sys

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from binance.client import Client
from config.config import API_KEY, API_SECRET, TESTNET
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_testnet_funds():
    """Add testnet funds to the account"""
    try:
        # Initialize client
        client = Client(API_KEY, API_SECRET, testnet=TESTNET)
        
        # Get current balances
        account = client.get_account()
        balances = {asset['asset']: float(asset['free']) for asset in account['balances']}
        
        logger.info("Current balances:")
        for asset, balance in balances.items():
            if balance > 0:
                logger.info(f"{asset}: {balance}")
        
        # Add USDT funds
        logger.info("\nAdding USDT funds...")
        for i in range(3):  # Try 3 times
            try:
                # Create a test order to add USDT
                order = client.create_test_order(
                    symbol='BTCUSDT',
                    side='BUY',
                    type='MARKET',
                    quantity=0.1
                )
                logger.info(f"Attempt {i+1}: Created test order for BTCUSDT")
                
                # Check new balance
                account = client.get_account()
                new_balances = {asset['asset']: float(asset['free']) for asset in account['balances']}
                logger.info(f"New USDT balance: {new_balances.get('USDT', 0)}")
                
            except Exception as e:
                logger.error(f"Error adding USDT: {e}")
        
        # Add AVAX funds
        logger.info("\nAdding AVAX funds...")
        for i in range(3):  # Try 3 times
            try:
                # Create a test order to add AVAX
                order = client.create_test_order(
                    symbol='AVAXUSDT',
                    side='BUY',
                    type='MARKET',
                    quantity=2.0
                )
                logger.info(f"Attempt {i+1}: Created test order for AVAXUSDT")
                
                # Check new balance
                account = client.get_account()
                new_balances = {asset['asset']: float(asset['free']) for asset in account['balances']}
                logger.info(f"New AVAX balance: {new_balances.get('AVAX', 0)}")
                
            except Exception as e:
                logger.error(f"Error adding AVAX: {e}")
        
        # Show final balances
        logger.info("\nFinal balances:")
        account = client.get_account()
        final_balances = {asset['asset']: float(asset['free']) for asset in account['balances']}
        for asset, balance in final_balances.items():
            if balance > 0:
                logger.info(f"{asset}: {balance}")
                
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    add_testnet_funds() 