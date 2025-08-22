"""
Script to analyze trades in Firestore
"""

import os
import sys
import logging

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from utils.database import TradingDatabase

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Initialize database
    db = TradingDatabase()
    
    # Analyze trades in both collections
    logger.info("Analyzing trades in default collection...")
    db.analyze_trades()
    
    logger.info("\nAnalyzing trades in backTestBot collection...")
    db.analyze_trades(collection_name="trades_backTestBot")

if __name__ == "__main__":
    main() 