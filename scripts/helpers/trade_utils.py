import logging
from datetime import datetime
import os
import shutil
import json
import glob

logger = logging.getLogger(__name__)

def execute_trade(symbol, trade_type, price, timestamp, strategy, position_size, timeframe, stop_loss_pct=0.02, take_profit_pct=0.06):
    """Execute a trade with the given parameters"""
    trade = {
        'symbol': symbol,
        'type': trade_type,
        'entry_price': price,
        'entry_time': timestamp,
        'position_size': position_size,
        'strategy': strategy,
        'timeframe': timeframe,
        'stop_loss': price * (1 - stop_loss_pct) if trade_type == 'LONG' else price * (1 + stop_loss_pct),
        'take_profit': price * (1 + take_profit_pct) if trade_type == 'LONG' else price * (1 - take_profit_pct),
        'exit_price': None,
        'exit_time': None,
        'profit': None,
        'exit_reason': None
    }
    
    logger.info(f"Executed {trade_type} trade for {symbol} at {price}")
    return trade

def update_open_positions(positions, current_price, timestamp, stop_loss_pct=0.02, take_profit_pct=0.06):
    """Update open positions and check for stop loss/take profit"""
    closed_positions = []
    
    for position in positions:
        # Check stop loss and take profit
        if position['type'] == 'LONG':
            stop_loss = position['entry_price'] * (1 - stop_loss_pct)
            take_profit = position['entry_price'] * (1 + take_profit_pct)
            
            if current_price <= stop_loss:
                position['exit_price'] = current_price
                position['exit_time'] = timestamp
                position['profit'] = (current_price - position['entry_price']) * position['position_size']
                position['exit_reason'] = 'stop_loss'
                closed_positions.append(position)
            elif current_price >= take_profit:
                position['exit_price'] = current_price
                position['exit_time'] = timestamp
                position['profit'] = (current_price - position['entry_price']) * position['position_size']
                position['exit_reason'] = 'take_profit'
                closed_positions.append(position)
        else:  # SHORT
            stop_loss = position['entry_price'] * (1 + stop_loss_pct)
            take_profit = position['entry_price'] * (1 - take_profit_pct)
            
            if current_price >= stop_loss:
                position['exit_price'] = current_price
                position['exit_time'] = timestamp
                position['profit'] = (position['entry_price'] - current_price) * position['position_size']
                position['exit_reason'] = 'stop_loss'
                closed_positions.append(position)
            elif current_price <= take_profit:
                position['exit_price'] = current_price
                position['exit_time'] = timestamp
                position['profit'] = (position['entry_price'] - current_price) * position['position_size']
                position['exit_reason'] = 'take_profit'
                closed_positions.append(position)
    
    # Remove closed positions from open positions
    for position in closed_positions:
        positions.remove(position)
    
    return closed_positions

def backup_trade_history(filename):
    """Create a backup of the trade history file"""
    if not os.path.exists(filename):
        logger.warning(f"No trade history file found at {filename}")
        return
    
    backup_dir = os.path.join(os.path.dirname(filename), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = os.path.join(backup_dir, f'trade_history_{timestamp}.json')
    
    shutil.copy2(filename, backup_filename)
    logger.info(f"Created backup at {backup_filename}")

def restore_from_backup(filename):
    """Restore trade history from the most recent backup"""
    backup_dir = os.path.join(os.path.dirname(filename), 'backups')
    if not os.path.exists(backup_dir):
        logger.warning("No backup directory found")
        return None
    
    backup_files = glob.glob(os.path.join(backup_dir, 'trade_history_*.json'))
    if not backup_files:
        logger.warning("No backup files found")
        return None
    
    latest_backup = max(backup_files, key=os.path.getctime)
    shutil.copy2(latest_backup, filename)
    logger.info(f"Restored from backup: {latest_backup}")
    
    return load_trade_history(filename) 