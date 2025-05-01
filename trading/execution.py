from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging
import math

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self, client, symbol, test_mode=True):
        self.client = client
        self.symbol = symbol
        self.test_mode = test_mode
        
        # Get symbol info for proper quantity formatting
        self.symbol_info = self._get_symbol_info()
    
    def _get_symbol_info(self):
        """Get trading rules for this symbol"""
        try:
            exchange_info = self.client.get_exchange_info()
            for symbol_info in exchange_info['symbols']:
                if symbol_info['symbol'] == self.symbol:
                    return symbol_info
            return None
        except BinanceAPIException as e:
            logger.error(f"Error getting symbol info: {e}")
            return None
    
    def _format_quantity(self, quantity):
        """Format quantity according to symbol's lot size rules"""
        if self.symbol_info is None:
            # If we can't get symbol info, use default formatting (6 decimal places)
            return "{:.6f}".format(quantity).rstrip('0').rstrip('.')
        
        # Find the LOT_SIZE filter
        lot_size = None
        for filter_item in self.symbol_info['filters']:
            if filter_item['filterType'] == 'LOT_SIZE':
                lot_size = filter_item
                break
        
        if lot_size is None:
            # Default to 6 decimal places if we can't find the filter
            return "{:.6f}".format(quantity).rstrip('0').rstrip('.')
        
        # Calculate step size precision
        step_size = float(lot_size['stepSize'])
        precision = 0
        if '.' in lot_size['stepSize']:
            precision = len(lot_size['stepSize'].split('.')[1].rstrip('0'))
        
        # Round quantity to step size
        step_size = float(lot_size['stepSize'])
        quantity = math.floor(quantity / step_size) * step_size
        
        # Format to correct precision
        formatted_qty = "{:.{}f}".format(quantity, precision)
        
        # Check minimum quantity
        min_qty = float(lot_size['minQty'])
        if quantity < min_qty:
            logger.warning(f"Calculated quantity {quantity} is below minimum {min_qty}, using minimum")
            return "{:.{}f}".format(min_qty, precision)
        
        return formatted_qty
    
    def get_account_balance(self, asset='USDT'):
        """Get available balance for a specific asset"""
        try:
            account = self.client.get_account()
            for balance in account['balances']:
                if balance['asset'] == asset:
                    return float(balance['free'])
            return 0
        except BinanceAPIException as e:
            logger.error(f"Error getting balance: {e}")
            return 0
    
    def place_market_order(self, side, quantity):
        """Place a market order"""
        try:
            # Format quantity properly according to symbol rules
            formatted_quantity = self._format_quantity(quantity)
            
            if self.test_mode:
                # Test order - doesn't actually execute
                order = self.client.create_test_order(
                    symbol=self.symbol,
                    side=side,
                    type='MARKET',
                    quantity=formatted_quantity
                )
                logger.info(f"TEST ORDER: {self.symbol} {side} {formatted_quantity}")
                return order
            
            # Get current price for value calculation
            ticker = self.client.get_symbol_ticker(symbol=self.symbol)
            current_price = float(ticker['price'])
            value_usd = current_price * float(formatted_quantity)
            
            # Place actual order
            order = self.client.create_order(
                symbol=self.symbol,
                side=side,
                type='MARKET',
                quantity=formatted_quantity
            )
            
            # Log concise order info
            status = order.get('status', 'UNKNOWN')
            logger.info(f"{self.symbol} {side} {formatted_quantity} (${value_usd:.2f}) - {status}")
            
            return order
        except Exception as e:
            logger.error(f"Error placing {side} order for {self.symbol}: {e}")
            return None
    
    def calculate_position_size(self, price, risk_percent=1.0, stop_loss_percent=2.0):
        """Calculate position size based on risk parameters"""
        usdt_balance = self.get_account_balance('USDT')
        risk_amount = usdt_balance * (risk_percent / 100)
        stop_loss_amount = price * (stop_loss_percent / 100)
        
        # Calculate quantity based on risk
        raw_quantity = risk_amount / stop_loss_amount
        
        # For altcoins with lower prices, adjust minimum quantity
        if 'SOL' in self.symbol:
            # Ensure we have at least 0.1 SOL for example
            raw_quantity = max(raw_quantity, 0.1)
        elif 'ETH' in self.symbol:
            # Ensure we have at least 0.01 ETH
            raw_quantity = max(raw_quantity, 0.01)
        elif 'BTC' in self.symbol:
            # BTC is expensive, so even small amounts are fine
            raw_quantity = max(raw_quantity, 0.001)
        
        return raw_quantity
    
    def place_market_order_with_trailing_stop(self, side, quantity, trailing_percent=1.0):
        """Place a market order with a trailing stop loss"""
        try:
            # Format quantity properly
            formatted_quantity = self._format_quantity(quantity)
            logger.info(f"Formatted order quantity: {formatted_quantity} for {self.symbol} with {trailing_percent}% trailing stop")
            
            if self.test_mode:
                # Test order
                logger.info(f"TEST ORDER: {side} {formatted_quantity} {self.symbol} with trailing stop")
                return {"status": "TEST", "side": side, "quantity": formatted_quantity}
            else:
                # Place the initial market order
                order = self.client.create_order(
                    symbol=self.symbol,
                    side=side,
                    type='MARKET',
                    quantity=formatted_quantity
                )
                
                # Get the execution price
                fills = order.get('fills', [])
                if not fills:
                    logger.warning("No fill information available for trailing stop")
                    return order
                    
                # Calculate average execution price
                total_qty = sum(float(fill['qty']) for fill in fills)
                total_value = sum(float(fill['qty']) * float(fill['price']) for fill in fills)
                avg_price = total_value / total_qty if total_qty > 0 else 0
                
                # Set up trailing stop parameters
                activation_price = None
                if side == 'BUY':
                    # For long positions, set stop below entry
                    callback_rate = trailing_percent
                else:
                    # For short positions, set stop above entry
                    callback_rate = trailing_percent
                    
                # Place trailing stop order
                stop_order = self.client.create_order(
                    symbol=self.symbol,
                    side='SELL' if side == 'BUY' else 'BUY',  # Opposite of entry
                    type='TRAILING_STOP_MARKET',
                    quantity=formatted_quantity,
                    callbackRate=callback_rate
                )
                
                logger.info(f"Placed trailing stop: {stop_order}")
                return {**order, 'trailing_stop': stop_order}
                
        except BinanceAPIException as e:
            logger.error(f"Order failed: {e}")
            return None