import pandas as pd
from datetime import datetime

def process_dataframe(df):
    """
    Process a DataFrame by adding combo column, formatting numbers, and adding timestamp.
    This function is used by both backTestBot.py and upload_to_sheets.py.
    
    Args:
        df (pandas.DataFrame): Input DataFrame
        
    Returns:
        pandas.DataFrame: Processed DataFrame
    """
    # Add combo column
    df['combo'] = df['pair'] + ' - ' + df['strategy'] + ' - ' + df['period']
    
    # Format numeric columns
    numeric_cols = ['profit', 'fees']
    for col in numeric_cols:
        if col in df.columns:
            # Handle both string and numeric values
            if df[col].dtype == 'object':
                df[col] = pd.to_numeric(df[col].str.replace('$', '').str.replace(',', ''), errors='coerce')
            df[col] = df[col].round(2)
    
    # Add Last Updated timestamp
    df['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return df