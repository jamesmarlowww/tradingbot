"""
Script to demonstrate running different bot types
"""

import os
import sys
import subprocess
import logging

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_backtest_bot():
    """Run the backtest bot with 'backTestBot' run name"""
    logger.info("Running backtest bot...")
    
    # Set environment variable for this run
    env = os.environ.copy()
    env['RUN_NAME'] = 'backTestBot'
    
    # Run the backtest bot
    result = subprocess.run([sys.executable, 'scripts/backTestBot.py'], 
                          env=env, cwd=root_dir)
    
    if result.returncode == 0:
        logger.info("Backtest bot completed successfully")
    else:
        logger.error("Backtest bot failed")
    
    return result.returncode

def run_prod_bot():
    """Run the production bot with 'prod' run name"""
    logger.info("Running production bot...")
    
    # Set environment variable for this run
    env = os.environ.copy()
    env['RUN_NAME'] = 'prod'
    
    # Run the production bot (assuming it exists)
    result = subprocess.run([sys.executable, 'scripts/prodTradingBot.py'], 
                          env=env, cwd=root_dir)
    
    if result.returncode == 0:
        logger.info("Production bot completed successfully")
    else:
        logger.error("Production bot failed")
    
    return result.returncode

def run_live_test_bot():
    """Run the live trading test bot with 'liveTradingTest' run name"""
    logger.info("Running live trading test bot...")
    
    # Set environment variable for this run
    env = os.environ.copy()
    env['RUN_NAME'] = 'liveTradingTest'
    
    # Run the test bot (assuming it exists)
    result = subprocess.run([sys.executable, 'scripts/testTradingBot.py'], 
                          env=env, cwd=root_dir)
    
    if result.returncode == 0:
        logger.info("Live trading test bot completed successfully")
    else:
        logger.error("Live trading test bot failed")
    
    return result.returncode

def main():
    print("="*60)
    print("BOT TYPE RUNNER")
    print("="*60)
    print("This script demonstrates how to run different bot types")
    print("Each bot type will be stored with a different 'run_name' in BigQuery")
    print()
    print("Available bot types:")
    print("1. backTestBot - For backtesting strategies")
    print("2. prod - For production trading")
    print("3. liveTradingTest - For live trading tests")
    print()
    
    choice = input("Enter your choice (1-3) or 'q' to quit: ").strip()
    
    if choice == '1':
        run_backtest_bot()
    elif choice == '2':
        run_prod_bot()
    elif choice == '3':
        run_live_test_bot()
    elif choice.lower() == 'q':
        print("Exiting...")
    else:
        print("Invalid choice. Please enter 1, 2, 3, or q.")

if __name__ == "__main__":
    main() 