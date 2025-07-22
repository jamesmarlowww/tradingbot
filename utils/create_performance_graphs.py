import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime
import logging
import sys

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('data/logs/graph_generation.log')
    ]
)
logger = logging.getLogger(__name__)

def check_file_exists(filepath):
    if not os.path.exists(filepath):
        logger.error(f"File does not exist: {filepath}")
        return False
    if os.path.getsize(filepath) == 0:
        logger.error(f"File is empty: {filepath}")
        return False
    return True

try:
    # Check if output directory exists
    if not os.path.exists('output'):
        logger.error("Output directory does not exist!")
        sys.exit(1)
        
    # Check if summary reports exist and are not empty
    overall_report = 'output/summary_report_overall.csv'
    daily_report = 'output/summary_report_daily.csv'
    
    if not check_file_exists(overall_report):
        logger.error("Overall report is missing or empty!")
        sys.exit(1)
    if not check_file_exists(daily_report):
        logger.error("Daily report is missing or empty!")
        sys.exit(1)
    
    # Read both summary reports
    logger.info("Reading summary reports...")
    df_overall = pd.read_csv(overall_report)
    df_daily = pd.read_csv(daily_report)
    
    logger.info(f"Overall report shape: {df_overall.shape}")
    logger.info(f"Daily report shape: {df_daily.shape}")
    
    if df_overall.empty or df_daily.empty:
        logger.error("One or both dataframes are empty!")
        sys.exit(1)
    
    # Convert profit columns from string to float for both dataframes
    def convert_profit(profit_str):
        try:
            # Remove $ and , then convert to float
            return float(str(profit_str).replace('$', '').replace(',', ''))
        except Exception as e:
            logger.error(f"Error converting profit value: {profit_str}, Error: {e}")
            return 0.0
    
    logger.info("Converting profit columns...")
    df_overall['total_profit'] = df_overall['total_profit'].apply(convert_profit)
    df_overall['profit_after_fees'] = df_overall['profit_after_fees'].apply(convert_profit)
    df_daily['total_profit'] = df_daily['total_profit'].apply(convert_profit)
    df_daily['profit_after_fees'] = df_daily['profit_after_fees'].apply(convert_profit)
    
    # Convert date column to datetime
    df_daily['date'] = pd.to_datetime(df_daily['date'])
    
    # Create output directory if it doesn't exist
    graphs_dir = 'output/graphs'
    os.makedirs(graphs_dir, exist_ok=True)
    logger.info(f"Created/verified graphs directory: {graphs_dir}")
    
    # Set figure style
    plt.style.use('default')
    sns.set_theme(style="whitegrid")
    
    # Original bar charts
    # 1. Performance by Period
    logger.info("Generating Performance by Period bar chart...")
    
    # Calculate profits and trade counts for each period
    period_data = df_overall.groupby('period').agg({
        'profit_after_fees': 'sum',
        'total_trades': 'sum'
    }).sort_values('profit_after_fees', ascending=False)
    
    if period_data.empty:
        logger.error("No period data available for plotting!")
        sys.exit(1)
    
    # Create figure and first axis
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Create bar chart for profits
    bars = ax1.bar(range(len(period_data)), period_data['profit_after_fees'], color='blue', alpha=0.6)
    ax1.set_xlabel('Period')
    ax1.set_ylabel('Total Profit After Fees ($)', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    
    # Set x-axis ticks and labels
    ax1.set_xticks(range(len(period_data)))
    ax1.set_xticklabels(period_data.index)
    
    # Add value labels on top of each bar
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                 f'${height:.2f}',
                 ha='center', va='bottom')

    # Create second axis for number of trades
    ax2 = ax1.twinx()
    ax2.plot(range(len(period_data)), period_data['total_trades'], 'r-', linewidth=2, marker='o')
    ax2.set_ylabel('Number of Trades', color='red')
    ax2.tick_params(axis='y', labelcolor='red')

    plt.title('Performance by Period')
    plt.grid(True)
    plt.tight_layout()
    
    # Save the figure
    output_path = os.path.join(graphs_dir, 'performance_by_period.png')
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved Performance by Period chart to: {output_path}")
    
    # 2. Performance by Strategy
    logger.info("Generating Performance by Strategy bar chart...")
    
    # Debug logging for strategy data
    logger.info(f"df_overall columns: {df_overall.columns}")
    logger.info(f"df_overall shape: {df_overall.shape}")
    logger.info(f"Unique strategies in df_overall: {df_overall['strategy'].unique()}")
    logger.info(f"Sample strategy data:\n{df_overall[['strategy', 'profit_after_fees', 'total_trades']].head()}")
    
    # Get unique strategies and their data
    strategies = df_overall['strategy'].unique()
    logger.info(f"Strategies to plot: {strategies}")
    
    # Convert profit columns to numeric if they're strings
    for col in ['total_profit', 'profit_after_fees']:
        if pd.api.types.is_string_dtype(df_overall[col]):
            df_overall[col] = pd.to_numeric(
                df_overall[col].str.replace('$', '').str.replace(',', ''), 
                errors='coerce'
            )
    
    profits = []
    trades = []
    
    for strategy in strategies:
        strategy_data = df_overall[df_overall['strategy'] == strategy]
        profit = strategy_data['profit_after_fees'].sum()
        trade_count = strategy_data['total_trades'].sum()
        logger.info(f"Strategy: {strategy}, Profit: {profit}, Trades: {trade_count}")
        profits.append(profit)
        trades.append(trade_count)
    
    logger.info(f"Final profits list: {profits}")
    logger.info(f"Final trades list: {trades}")
    
    # Create figure and first axis
    fig, ax1 = plt.subplots(figsize=(15, 8))
    
    # Create bar chart for profits
    x = range(len(strategies))
    logger.info(f"X-axis values: {x}")
    bars = ax1.bar(x, profits, color='blue', alpha=0.6)
    ax1.set_xlabel('Strategy')
    ax1.set_ylabel('Total Profit After Fees ($)', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    
    # Set x-axis ticks and labels
    ax1.set_xticks(x)
    ax1.set_xticklabels(strategies, rotation=45, ha='right')
    
    # Add value labels on top of each bar
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                 f'${height:.2f}',
                 ha='center', va='bottom')

    # Create second axis for number of trades
    ax2 = ax1.twinx()
    ax2.plot(x, trades, 'r-', linewidth=2, marker='o')
    ax2.set_ylabel('Number of Trades', color='red')
    ax2.tick_params(axis='y', labelcolor='red')

    plt.title('Performance by Strategy')
    plt.grid(True)
    plt.tight_layout()

    # Save the figure
    output_path = os.path.join(graphs_dir, 'performance_by_strategy.png')
    plt.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close()
    logger.info(f"Saved Performance by Strategy chart to: {output_path}")
    
    logger.info("Performance by Strategy bar chart generated.")
    
    # 3. Performance by Trading Pair
    logger.info("Generating Performance by Trading Pair bar chart...")
    plt.figure(figsize=(12, 6))
    
    # Calculate profits and trade counts for each pair
    pair_data = df_overall.groupby('pair').agg({
        'profit_after_fees': 'sum',
        'total_trades': 'sum'
    }).sort_values('profit_after_fees', ascending=False)
    
    # Create figure and first axis
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Create bar chart for profits
    bars = ax1.bar(range(len(pair_data)), pair_data['profit_after_fees'], color='blue', alpha=0.6)
    ax1.set_xlabel('Trading Pair')
    ax1.set_ylabel('Total Profit After Fees ($)', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    
    # Set x-axis ticks and labels
    ax1.set_xticks(range(len(pair_data)))
    ax1.set_xticklabels(pair_data.index, rotation=45)
    
    # Add value labels on top of each bar
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                 f'${height:.2f}',
                 ha='center', va='bottom')

    # Create second axis for number of trades
    ax2 = ax1.twinx()
    ax2.plot(range(len(pair_data)), pair_data['total_trades'], 'r-', linewidth=2, marker='o')
    ax2.set_ylabel('Number of Trades', color='red')
    ax2.tick_params(axis='y', labelcolor='red')

    plt.title('Performance by Trading Pair')
    plt.grid(True)
    plt.tight_layout()
    output_path = os.path.join(graphs_dir, 'performance_by_pair.png')
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved Performance by Trading Pair chart to: {output_path}")
    
    # 4. Top 10 Combined Performance
    logger.info("Generating Top 10 Combined Performance bar chart...")
    plt.figure(figsize=(15, 8))
    
    # Create combined key
    df_overall['combined_key'] = df_overall['period'] + ' - ' + df_overall['strategy'] + ' - ' + df_overall['pair']
    
    # Calculate profits and trade counts for each combination
    combined_data = df_overall.groupby('combined_key').agg({
        'profit_after_fees': 'sum',
        'total_trades': 'sum'
    }).sort_values('profit_after_fees', ascending=False).head(10)
    
    # Create figure and first axis
    fig, ax1 = plt.subplots(figsize=(15, 8))
    
    # Create bar chart for profits
    bars = ax1.bar(range(len(combined_data)), combined_data['profit_after_fees'], color='blue', alpha=0.6)
    ax1.set_xlabel('Period - Strategy - Pair')
    ax1.set_ylabel('Total Profit After Fees ($)', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    
    # Set x-axis ticks and labels
    ax1.set_xticks(range(len(combined_data)))
    ax1.set_xticklabels(combined_data.index, rotation=45, ha='right')
    
    # Add value labels on top of each bar
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                 f'${height:.2f}',
                 ha='center', va='bottom')

    # Create second axis for number of trades
    ax2 = ax1.twinx()
    ax2.plot(range(len(combined_data)), combined_data['total_trades'], 'r-', linewidth=2, marker='o')
    ax2.set_ylabel('Number of Trades', color='red')
    ax2.tick_params(axis='y', labelcolor='red')

    plt.title('Top 10 Performance by Combined Key')
    plt.grid(True)
    plt.tight_layout()
    output_path = os.path.join(graphs_dir, 'performance_by_combined_key.png')
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved Top 10 Combined Performance chart to: {output_path}")
    
    # New line graphs showing performance over time
    # 1. Performance by Period over Time
    plt.figure(figsize=(12, 6))
    for period in df_daily['period'].unique():
        period_data = df_daily[df_daily['period'] == period].groupby('date')['profit_after_fees'].sum().cumsum()
        plt.plot(period_data.index, period_data.values, label=period, linewidth=2)
    plt.title('Cumulative Performance by Period over Time')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Profit After Fees ($)')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    output_path = os.path.join(graphs_dir, 'performance_by_period_by_date.png')
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved Cumulative Performance by Period over Time chart to: {output_path}")
    
    # 2. Performance by Strategy over Time
    plt.figure(figsize=(12, 6))
    for strategy in df_daily['strategy'].unique():
        strategy_data = df_daily[df_daily['strategy'] == strategy].groupby('date')['profit_after_fees'].sum().cumsum()
        plt.plot(strategy_data.index, strategy_data.values, label=strategy, linewidth=2)
    plt.title('Cumulative Performance by Strategy over Time')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Profit After Fees ($)')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    output_path = os.path.join(graphs_dir, 'performance_by_strategy_by_date.png')
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved Cumulative Performance by Strategy over Time chart to: {output_path}")
    
    # 3. Performance by Trading Pair over Time
    plt.figure(figsize=(12, 6))
    for pair in df_daily['pair'].unique():
        pair_data = df_daily[df_daily['pair'] == pair].groupby('date')['profit_after_fees'].sum().cumsum()
        plt.plot(pair_data.index, pair_data.values, label=pair, linewidth=2)
    plt.title('Cumulative Performance by Trading Pair over Time')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Profit After Fees ($)')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    output_path = os.path.join(graphs_dir, 'performance_by_pair_by_date.png')
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved Cumulative Performance by Trading Pair over Time chart to: {output_path}")
    
    # 4. Top 10 Combined Performance over Time
    df_daily['combined_key'] = df_daily['period'] + ' - ' + df_daily['strategy'] + ' - ' + df_daily['pair']
    top_10_keys = df_daily.groupby('combined_key')['profit_after_fees'].sum().nlargest(10).index
    plt.figure(figsize=(15, 8))
    for key in top_10_keys:
        key_data = df_daily[df_daily['combined_key'] == key].groupby('date')['profit_after_fees'].sum().cumsum()
        plt.plot(key_data.index, key_data.values, label=key, linewidth=2)
    plt.title('Cumulative Performance by Top 10 Combinations over Time')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Profit After Fees ($)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    output_path = os.path.join(graphs_dir, 'performance_by_combined_key_by_date.png')
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved Cumulative Performance by Top 10 Combinations over Time chart to: {output_path}")
    
    logger.info("All charts generated successfully!")
    
except Exception as e:
    logger.error(f"Error generating charts: {str(e)}", exc_info=True)
    sys.exit(1) 