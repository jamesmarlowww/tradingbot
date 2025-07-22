import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from datetime import datetime
from data_processing import process_dataframe
import logging

# Google Sheets configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1x6avfD43cyeD9NM1Yu0Bl9A525kXjbpDUBuO4EOswbo'
SERVICE_ACCOUNT_FILE = 'config/tradingbot-gSheets-API-Key.json'

# Set up logging
logger = logging.getLogger(__name__)

def get_google_sheets_service():
    """Create and return Google Sheets service."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials)
    return service

def ensure_sheet_exists(service, sheet_name):
    """Check if sheet exists and create it if it doesn't."""
    try:
        # Get spreadsheet metadata
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = spreadsheet.get('sheets', [])
        
        # Check if sheet exists
        sheet_exists = any(sheet['properties']['title'] == sheet_name for sheet in sheets)
        
        if not sheet_exists:
            # Create new sheet
            request = {
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={'requests': [request]}
            ).execute()
            print(f"Created new sheet: {sheet_name}")
        
        return True
    except Exception as e:
        print(f"Error ensuring sheet exists: {str(e)}")
        return False

def update_google_sheet(service, sheet_name, data):
    """Update a specific sheet with data."""
    try:
        # Ensure sheet exists
        if not ensure_sheet_exists(service, sheet_name):
            return False
            
        # Convert DataFrame to list of lists
        values = [data.columns.tolist()] + data.values.tolist()
        
        # Prepare the request
        body = {
            'values': values
        }
        
        # Update the sheet using A1 notation without quotes
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A1",
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"Updated {result.get('updatedCells')} cells in {sheet_name}")
        return True
    except Exception as e:
        print(f"Error updating {sheet_name}: {str(e)}")
        return False

def process_dataframe(df):
    """Process DataFrame before uploading to sheets"""
    try:
        # Log initial record count
        logger.info(f"Processing DataFrame with {len(df)} records")
        
        # Add combo column
        df['combo'] = df['pair'] + ' - ' + df['strategy'] + ' - ' + df['period']
        
        # Format numeric columns
        numeric_cols = ['total_profit', 'profit_after_fees']
        for col in numeric_cols:
            if col in df.columns:
                # Handle both string and numeric values
                if df[col].dtype == 'object':
                    df[col] = pd.to_numeric(df[col].str.replace('$', '').str.replace(',', ''), errors='coerce')
                df[col] = df[col].round(2)
        
        # Add timestamp
        df['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Log final record count
        logger.info(f"Processed DataFrame has {len(df)} records")
        
        return df
    except Exception as e:
        logger.error(f"Error processing DataFrame: {str(e)}")
        raise

def upload_to_sheets():
    try:
        # Set up credentials
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
        
        # Build the Sheets API service
        service = build('sheets', 'v4', credentials=credentials)
        
        # Define sheet configurations
        SHEET_CONFIG = {
            'summary_report_overall.csv': [
                'date', 'pair', 'strategy', 'period', 
                'total_trades', 'total_profit', 
                'winning_trades', 'win_rate', 'profit_after_fees'
            ],
            'summary_report_daily.csv': [
                'date', 'pair', 'strategy', 'period',
                'trades', 'profit', 'balance'
            ]
        }
        
        success_count = 0
        total_files = len(SHEET_CONFIG)
        
        # Process each CSV file
        for csv_file, sheet_config in SHEET_CONFIG.items():
            try:
                # Read the CSV file
                df = pd.read_csv(f'output/{csv_file}')
                logger.info(f"Read {len(df)} records from {csv_file}")
                
                # Process the DataFrame
                df = process_dataframe(df)
                logger.info(f"Processed DataFrame has {len(df)} records")
                
                # Log sample of processed data
                logger.info("Sample of processed data:")
                logger.info(df.head().to_string())
                
                # Convert to list of lists
                values = [df.columns.tolist()] + df.values.tolist()
                
                # Clear the sheet
                sheet_name = csv_file.replace('.csv', '').replace('summary_report_', '')
                # Properly format sheet name for Google Sheets API
                sheet_name = sheet_name.replace('_', ' ')  # Replace underscores with spaces
                clear_range = f"'{sheet_name}'!A1:Z1000"  # Add quotes around sheet name
                service.spreadsheets().values().clear(
                    spreadsheetId=SPREADSHEET_ID,
                    range=clear_range
                ).execute()
                
                # Update the sheet
                body = {'values': values}
                result = service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=f"'{sheet_name}'!A1",  # Add quotes around sheet name
                    valueInputOption='RAW',
                    body=body
                ).execute()
                
                logger.info(f"Successfully uploaded {sheet_name}")
                logger.info(f"Updated {result.get('updatedCells')} cells")
                success_count += 1
                
            except Exception as e:
                logger.error(f"Error processing {csv_file}: {str(e)}")
                continue
        
        # Return success status
        return success_count == total_files, success_count, total_files
            
    except Exception as e:
        logger.error(f"Error uploading to Google Sheets: {str(e)}")
        return False, 0, total_files

if __name__ == "__main__":
    success, success_count, total_files = upload_to_sheets()
    if success:
        print(f"\n✓ Successfully uploaded all {total_files} files to Google Sheets")
    else:
        print(f"\n✗ Upload incomplete: {success_count}/{total_files} files uploaded successfully") 