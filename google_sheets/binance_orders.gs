// Configuration
const API_KEY = 'BYNH4WgKmLmtj21RZvTT0S93pbcrOmuZAcpRfOsfMMfits6EtlGm2J6GgtNOz9IL';
const API_SECRET = 'q0488lbBijChSHhRfgoFvLwAwXjxSK0KFW7aLn6F2gikO3U7JED6RU5WHtpaZp5m';
const BASE_URL = 'https://testnet.binance.vision';

// Trading pairs to track
const TRADING_PAIRS = [
  'BTCUSDT',
  'ETHUSDT',
  'SOLUSDT',
  'AVAXUSDT'
];

function getBinanceOrders() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Orders') || 
                SpreadsheetApp.getActiveSpreadsheet().insertSheet('Orders');
  sheet.clear();
  
  // Add headers
  const headers = [
    'Symbol',
    'OrderId',
    'ClientOrderId',
    'Price',
    'OrigQty',
    'ExecutedQty',
    'CummulativeQuoteQty',
    'Status',
    'TimeInForce',
    'Type',
    'Side',
    'StopPrice',
    'IcebergQty',
    'Time',
    'UpdateTime',
    'IsWorking',
    'OrigQuoteOrderQty'
  ];
  sheet.appendRow(headers);
  
  // Get orders for each trading pair
  TRADING_PAIRS.forEach(symbol => {
    try {
      const orders = fetchOrders(symbol);
      if (orders && orders.length > 0) {
        orders.forEach(order => {
          const row = headers.map(header => {
            const value = order[header.toLowerCase()];
            // Format timestamp to readable date
            if (header === 'Time' || header === 'UpdateTime') {
              return value ? new Date(value).toLocaleString() : '';
            }
            // Format numbers
            if (typeof value === 'number') {
              return value.toFixed(8);
            }
            return value || '';
          });
          sheet.appendRow(row);
        });
      }
    } catch (error) {
      console.error(`Error fetching orders for ${symbol}:`, error);
      sheet.appendRow([symbol, 'Error fetching orders', error.toString()]);
    }
  });
  
  // Auto-resize columns
  sheet.autoResizeColumns(1, headers.length);
  
  // Add some formatting
  sheet.setFrozenRows(1);
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setBackground('#f3f3f3').setFontWeight('bold');
}

function fetchOrders(symbol) {
  const timestamp = Date.now();
  const query = `symbol=${symbol}&timestamp=${timestamp}`;
  const signature = Utilities.computeHmacSha256Signature(query, API_SECRET);
  const signatureHex = signature.map(b => ('0' + (b & 0xFF).toString(16)).slice(-2)).join('');

  const url = `${BASE_URL}/api/v3/allOrders?${query}&signature=${signatureHex}`;

  const options = {
    method: 'get',
    headers: {
      'X-MBX-APIKEY': API_KEY
    },
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(url, options);
  return JSON.parse(response.getContentText());
}

// Create a menu item to run the script
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('Binance Tools')
    .addItem('Fetch Orders', 'getBinanceOrders')
    .addToUi();
} 