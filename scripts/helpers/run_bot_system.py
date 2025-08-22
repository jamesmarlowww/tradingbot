#!/usr/bin/env python3
"""
Complete Bot System Runner

This script demonstrates how to run the complete trading bot system:

1. Daily Monitor (backTestBot in monitor mode) - runs continuously
2. Test Bot - runs only when 5+ day positive streaks are detected
3. Production Bot - runs only when conditions are met

Usage:
    python scripts/run_bot_system.py --mode monitor    # Start daily monitoring
    python scripts/run_bot_system.py --mode test       # Start test bot
    python scripts/run_bot_system.py --mode prod       # Start production bot
    python scripts/run_bot_system.py --mode all        # Start all components
"""

import os
import sys
import subprocess
import time
import argparse
import logging
from datetime import datetime

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from utils.bot_core import BotCore
from config.automation_config import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/logs/bot_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_daily_monitor():
    """Start the daily monitoring bot (monitorBot)"""
    logger.info("Starting daily monitoring bot...")
    
    try:
        # Run monitorBot in comprehensive monitoring mode
        cmd = [
            sys.executable, 
            'scripts/monitorBot.py', 
            '--schedule', 'comprehensive'
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        logger.info(f"Daily monitor started with PID: {process.pid}")
        return process
        
    except Exception as e:
        logger.error(f"Failed to start daily monitor: {e}")
        return None

def run_test_bot():
    """Start the test bot"""
    logger.info("Starting test bot...")
    
    try:
        # Run testTradingBot
        cmd = [sys.executable, 'scripts/testTradingBot.py']
        
        logger.info(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        logger.info(f"Test bot started with PID: {process.pid}")
        return process
        
    except Exception as e:
        logger.error(f"Failed to start test bot: {e}")
        return None

def run_prod_bot():
    """Start the production bot"""
    logger.info("Starting production bot...")
    
    try:
        # Run prodTradingBot
        cmd = [sys.executable, 'scripts/prodTradingBot.py']
        
        logger.info(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        logger.info(f"Production bot started with PID: {process.pid}")
        return process
        
    except Exception as e:
        logger.error(f"Failed to start production bot: {e}")
        return None

def check_streak_conditions():
    """Check if trading should be enabled based on streak conditions"""
    try:
        # Use test bot core to check conditions
        bot_core = BotCore(bot_type='test', run_name='testBot')
        return bot_core.check_streak_conditions()
    except Exception as e:
        logger.error(f"Error checking streak conditions: {e}")
        return False

def monitor_and_control():
    """Monitor the system and control bot execution based on streak conditions"""
    logger.info("Starting system monitor and controller...")
    
    processes = {}
    
    try:
        while True:
            current_time = datetime.now()
            logger.info(f"System check at {current_time}")
            
            # Check streak conditions
            trading_enabled = check_streak_conditions()
            
            if trading_enabled:
                logger.info("🟢 Trading conditions met - bots should be running")
                
                # Start test bot if not running
                if 'test_bot' not in processes or processes['test_bot'].poll() is not None:
                    logger.info("Starting test bot...")
                    processes['test_bot'] = run_test_bot()
                
                # Start prod bot if not running (optional - more conservative)
                # if 'prod_bot' not in processes or processes['prod_bot'].poll() is not None:
                #     logger.info("Starting production bot...")
                #     processes['prod_bot'] = run_prod_bot()
                    
            else:
                logger.info("🔴 Trading conditions not met - stopping trading bots")
                
                # Stop test bot if running
                if 'test_bot' in processes and processes['test_bot'].poll() is None:
                    logger.info("Stopping test bot...")
                    processes['test_bot'].terminate()
                    processes['test_bot'].wait()
                    del processes['test_bot']
                
                # Stop prod bot if running
                if 'prod_bot' in processes and processes['prod_bot'].poll() is None:
                    logger.info("Stopping production bot...")
                    processes['prod_bot'].terminate()
                    processes['prod_bot'].wait()
                    del processes['prod_bot']
            
            # Clean up finished processes
            for name, process in list(processes.items()):
                if process.poll() is not None:
                    logger.info(f"Process {name} finished with return code: {process.returncode}")
                    del processes[name]
            
            # Wait before next check
            logger.info("Next system check in 1 hour...")
            time.sleep(3600)  # Check every hour
            
    except KeyboardInterrupt:
        logger.info("Shutting down system monitor...")
        
        # Terminate all running processes
        for name, process in processes.items():
            if process.poll() is None:
                logger.info(f"Terminating {name}...")
                process.terminate()
                process.wait()

def main():
    parser = argparse.ArgumentParser(description='Complete Bot System Runner')
    parser.add_argument('--mode', choices=['monitor', 'test', 'prod', 'all', 'control'], 
                       default='control', help='Run mode')
    parser.add_argument('--monitor-interval', type=int, default=3600,
                       help='Monitor interval in seconds (default: 3600)')
    
    args = parser.parse_args()
    
    print("=== COMPLETE BOT SYSTEM ===")
    print(f"Mode: {args.mode}")
    print(f"Monitor Interval: {args.monitor_interval} seconds")
    print("==========================\n")
    
    if args.mode == 'monitor':
        # Run only daily monitor
        process = run_daily_monitor()
        if process:
            try:
                process.wait()
            except KeyboardInterrupt:
                process.terminate()
                process.wait()
    
    elif args.mode == 'test':
        # Run only test bot
        process = run_test_bot()
        if process:
            try:
                process.wait()
            except KeyboardInterrupt:
                process.terminate()
                process.wait()
    
    elif args.mode == 'prod':
        # Run only production bot
        process = run_prod_bot()
        if process:
            try:
                process.wait()
            except KeyboardInterrupt:
                process.terminate()
                process.wait()
    
    elif args.mode == 'all':
        # Run all components
        processes = {}
        
        # Start daily monitor
        processes['monitor'] = run_daily_monitor()
        time.sleep(5)  # Give monitor time to start
        
        # Start test bot
        processes['test'] = run_test_bot()
        time.sleep(5)  # Give test bot time to start
        
        # Start production bot
        processes['prod'] = run_prod_bot()
        
        try:
            # Wait for all processes
            for name, process in processes.items():
                if process:
                    logger.info(f"Waiting for {name} process...")
                    process.wait()
        except KeyboardInterrupt:
            logger.info("Shutting down all processes...")
            for name, process in processes.items():
                if process and process.poll() is None:
                    process.terminate()
                    process.wait()
    
    elif args.mode == 'control':
        # Run the intelligent controller
        monitor_and_control()

if __name__ == "__main__":
    main() 