import pandas as pd
import numpy as np
from datetime import datetime
import logging
import os
import json

logger = logging.getLogger(__name__)

def generate_performance_report(trades, initial_balance):
    """Generate a comprehensive performance report"""
    if not trades:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_profit': 0,
            'average_profit': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'final_balance': initial_balance
        }
    
    # Calculate basic metrics
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t['profit'] > 0])
    losing_trades = len([t for t in trades if t['profit'] <= 0])
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    
    # Calculate profit metrics
    total_profit = sum(t['profit'] for t in trades)
    average_profit = total_profit / total_trades if total_trades > 0 else 0
    
    # Calculate drawdown
    balance_curve = [initial_balance]
    for trade in trades:
        balance_curve.append(balance_curve[-1] + trade['profit'])
    
    peak = balance_curve[0]
    max_drawdown = 0
    for balance in balance_curve:
        if balance > peak:
            peak = balance
        drawdown = (peak - balance) / peak
        max_drawdown = max(max_drawdown, drawdown)
    
    # Calculate Sharpe Ratio (assuming risk-free rate of 0)
    returns = pd.Series([t['profit'] for t in trades])
    sharpe_ratio = np.sqrt(252) * (returns.mean() / returns.std()) if len(returns) > 1 else 0
    
    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'total_profit': total_profit,
        'average_profit': average_profit,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'final_balance': balance_curve[-1]
    }

def export_summary_to_csv(summary_data, filename):
    """Export summary data to CSV file"""
    df = pd.DataFrame([summary_data])
    df.to_csv(filename, index=False)
    logger.info(f"Summary exported to {filename}")

def export_daily_summary_to_csv(daily_summary, filename):
    """Export daily summary data to CSV file"""
    try:
        # Log the raw data before conversion
        logger.info("Raw daily summary data:")
        for entry in daily_summary:
            logger.info(f"Entry: {entry}")
        
        # Convert to DataFrame
        df = pd.DataFrame(daily_summary)
        
        # Log the number of records before export
        logger.info(f"Exporting {len(df)} records to {filename}")
        
        # Define all time periods
        all_timeframes = ['15m', '30m', '1h', '2h', '4h', '1d']
        
        # Get unique values for each dimension
        all_pairs = df['pair'].unique()
        all_strategies = df['strategy'].unique()
        all_dates = df['date'].unique()
        
        # Log the unique values for debugging
        logger.info(f"Unique pairs: {all_pairs}")
        logger.info(f"Unique strategies: {all_strategies}")
        logger.info(f"Unique dates: {len(all_dates)}")
        
        # Check both timeframe and period columns
        if 'timeframe' in df.columns:
            logger.info(f"Unique timeframes in raw data: {df['timeframe'].unique()}")
            # Rename timeframe to period for consistency with CSV
            df = df.rename(columns={'timeframe': 'period'})
        elif 'period' in df.columns:
            logger.info(f"Unique periods in raw data: {df['period'].unique()}")
        else:
            logger.error("Neither timeframe nor period column found in data")
            return
        
        # Log the actual data in the DataFrame
        logger.info("DataFrame contents:")
        logger.info(df.to_string())
        
        # Create all possible combinations
        combinations = []
        for date in all_dates:
            for pair in all_pairs:
                for strategy in all_strategies:
                    for timeframe in all_timeframes:
                        combinations.append({
                            'date': date,
                            'pair': pair,
                            'strategy': strategy,
                            'timeframe': timeframe,
                            'balance': 0,
                            'trades': 0,
                            'profit': 0
                        })
        
        # Create DataFrame with all combinations
        complete_df = pd.DataFrame(combinations)
        
        # Set index for both dataframes
        df = df.set_index(['date', 'pair', 'strategy', 'timeframe'])
        complete_df = complete_df.set_index(['date', 'pair', 'strategy', 'timeframe'])
        
        # Update the complete DataFrame with actual data
        for idx, row in df.iterrows():
            if idx in complete_df.index:
                complete_df.loc[idx, ['balance', 'trades', 'profit']] = row[['balance', 'trades', 'profit']]
        
        # Reset index before writing
        complete_df = complete_df.reset_index()
        
        # Log the final timeframes in the DataFrame
        logger.info(f"Final timeframes in complete_df: {complete_df['timeframe'].unique()}")
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Write to CSV
        complete_df.to_csv(filename, index=False)
        
        # Verify the file was written correctly
        if os.path.exists(filename):
            verification_df = pd.read_csv(filename)
            logger.info(f"Verified {len(verification_df)} records in {filename}")
            
            # Verify all timeframes are present in the output file
            timeframes_in_file = verification_df['timeframe'].value_counts()
            logger.info("Record counts by timeframe:")
            for timeframe in all_timeframes:
                count = timeframes_in_file.get(timeframe, 0)
                logger.info(f"{timeframe}: {count} records")
                
            # Log the unique timeframes found in the file
            logger.info(f"Timeframes found in file: {verification_df['timeframe'].unique()}")
        else:
            logger.error(f"Failed to create file: {filename}")
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Write to CSV
        complete_df.to_csv(filename, index=False)
        
        # Verify the file was written correctly
        if os.path.exists(filename):
            verification_df = pd.read_csv(filename)
            logger.info(f"Verified {len(verification_df)} records in {filename}")
            
            # Verify all timeframes are present in the output file
            timeframes_in_file = verification_df['timeframe'].value_counts()
            logger.info("Record counts by timeframe:")
            for timeframe in all_timeframes:
                count = timeframes_in_file.get(timeframe, 0)
                logger.info(f"{timeframe}: {count} records")
                
            # Log the unique timeframes found in the file
            logger.info(f"Timeframes found in file: {verification_df['timeframe'].unique()}")
        else:
            logger.error(f"Failed to create file: {filename}")
            
    except Exception as e:
        logger.error(f"Error exporting daily summary to {filename}: {str(e)}")
        raise

def save_trade_history(trades, filename):
    """Save trade history to JSON file"""
    # Convert datetime objects to strings
    for trade in trades:
        trade['entry_time'] = trade['entry_time'].isoformat()
        trade['exit_time'] = trade['exit_time'].isoformat()
    
    with open(filename, 'w') as f:
        json.dump(trades, f, indent=4)
    logger.info(f"Trade history saved to {filename}")

def load_trade_history(filename):
    """Load trade history from JSON file"""
    try:
        with open(filename, 'r') as f:
            trades = json.load(f)
        
        # Convert string timestamps back to datetime objects
        for trade in trades:
            trade['entry_time'] = datetime.fromisoformat(trade['entry_time'])
            trade['exit_time'] = datetime.fromisoformat(trade['exit_time'])
        
        return trades
    except FileNotFoundError:
        logger.warning(f"Trade history file {filename} not found")
        return []
    except json.JSONDecodeError:
        logger.error(f"Error decoding trade history file {filename}")
        return []

def export_aggregated_summary_to_csv(daily_summaries, filename):
    """Export aggregated summary data to CSV file with date dimension"""
    try:
        logger.info(f"Starting export of aggregated summary to {filename}")
        logger.info(f"Number of daily summaries to process: {len(daily_summaries)}")
        
        if not daily_summaries:
            logger.error("No daily summaries to process - skipping file creation")
            return
            
        # Log the first entry to see its structure
        logger.info(f"First daily summary structure: {daily_summaries[0]}")
        
        # Convert daily summaries to DataFrame
        df = pd.DataFrame(daily_summaries)
        
        # Log the columns we have
        logger.info(f"Available columns: {df.columns.tolist()}")
        
        # Ensure we have the required columns
        required_columns = ['date', 'pair', 'strategy', 'period', 'trades', 'profit']
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            logger.error(f"First daily summary data: {daily_summaries[0] if daily_summaries else 'No data'}")
            return
            
        # Log date range
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
        
        # Group by date, pair, strategy, and period
        grouped = df.groupby(['date', 'pair', 'strategy', 'period']).agg({
            'trades': 'sum',
            'profit': 'sum'
        }).reset_index()
        
        # Rename columns to match expected format
        grouped.columns = ['date', 'pair', 'strategy', 'period', 'total_trades', 'total_profit']
        
        # Calculate winning trades and win rate
        winning_trades = df[df['profit'] > 0].groupby(['date', 'pair', 'strategy', 'period']).size().reset_index(name='winning_trades')
        grouped = grouped.merge(winning_trades, on=['date', 'pair', 'strategy', 'period'], how='left')
        grouped['winning_trades'] = grouped['winning_trades'].fillna(0)
        grouped['win_rate'] = (grouped['winning_trades'] / grouped['total_trades'] * 100).round(2)
        
        # Calculate profit after fees (assuming 0.1% fee)
        grouped['profit_after_fees'] = (grouped['total_profit'] * 0.998).round(2)
        
        # Sort by date, pair, strategy, and period
        grouped = grouped.sort_values(['date', 'pair', 'strategy', 'period'])
        
        # Select and rename columns to match summary_report_overall format
        final_df = grouped[[
            'date', 'pair', 'period', 'strategy', 'total_trades', 
            'total_profit', 'winning_trades', 'win_rate', 'profit_after_fees'
        ]]
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Write to CSV
        final_df.to_csv(filename, index=False)
        logger.info(f"Aggregated summary exported to {filename}")
        logger.info(f"Total records written: {len(final_df)}")
        
        # Verify the file was written correctly
        if os.path.exists(filename):
            verification_df = pd.read_csv(filename)
            logger.info(f"Verified {len(verification_df)} records in {filename}")
            
            # Log some statistics
            logger.info(f"Date range: {verification_df['date'].min()} to {verification_df['date'].max()}")
            logger.info(f"Unique pairs: {verification_df['pair'].unique()}")
            logger.info(f"Unique strategies: {verification_df['strategy'].unique()}")
            logger.info(f"Unique periods: {verification_df['period'].unique()}")
            
    except Exception as e:
        logger.error(f"Error exporting aggregated summary to {filename}: {str(e)}")
        logger.exception("Full traceback:")
        raise 