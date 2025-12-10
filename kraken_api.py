import krakenex
import time
import base64
import hashlib
import hmac
import urllib.parse
from typing import Optional, Tuple, Dict, Any

class KrakenAPI:
    def __init__(self, api_key: str = '', api_secret: str = '', sandbox: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox
        
        # Initialize krakenex client
        self.api = krakenex.API(key=api_key, secret=api_secret)
    
    def test_connection(self, api_key: str = None, api_secret: str = None, sandbox: bool = None) -> Tuple[bool, str]:
        """Test connection to Kraken API"""
        try:
            # Use provided credentials or stored ones
            key = api_key if api_key else self.api_key
            secret = api_secret if api_secret else self.api_secret
            sandbox_mode = sandbox if sandbox is not None else self.sandbox
            
            if not key or not secret:
                return False, "API key or secret missing"
            
            # Create temporary API instance for testing
            test_api = krakenex.API(key=key, secret=secret)
            
            # Test with balance query
            response = test_api.query_private('Balance')
            
            if response.get('error'):
                return False, f"API Error: {response['error']}"
            
            return True, "Connection successful"
            
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def get_ticker(self, pair: str) -> Optional[float]:
        """Get current ticker price for a pair"""
        try:
            # Convert pair format (BTC/USD -> XXBTZUSD)
            kraken_pair = self._convert_pair_to_kraken(pair)
            
            response = self.api.query_public('Ticker', {'pair': kraken_pair})
            
            if response.get('error'):
                print(f"Ticker error: {response['error']}")
                return None
            
            result = response.get('result', {})
            if kraken_pair in result:
                price_str = result[kraken_pair]['c'][0]  # Last trade closed
                return float(price_str)
            
            return None
            
        except Exception as e:
            print(f"Error getting ticker: {e}")
            return None
    
    def get_balance(self) -> Tuple[bool, float]:
        """Get account balance and calculate total USD value"""
        try:
            if not self.api_key:
                return False, 0.0
            
            response = self.api.query_private('Balance')
            
            if response.get('error'):
                print(f"Balance error: {response['error']}")
                return False, 0.0
            
            balances = response.get('result', {})
            
            # Calculate total USD value (simplified)
            total_usd = 0.0
            
            # Get current prices for major assets
            usd_pairs = {
                'XBT': 'XXBTZUSD',
                'ETH': 'XETHZUSD',
                'SOL': 'SOLUSD',
                'ADA': 'ADAUSD',
                'DOT': 'DOTUSD',
                'XRP': 'XRPUSD'
            }
            
            for asset, amount_str in balances.items():
                amount = float(amount_str)
                if amount <= 0.000001:  # Skip tiny amounts
                    continue
                
                if asset == 'ZUSD':  # USD
                    total_usd += amount
                elif asset in usd_pairs:
                    # Get current price
                    price = self.get_ticker_from_cache(usd_pairs[asset])
                    if price:
                        total_usd += amount * price
            
            return True, total_usd
            
        except Exception as e:
            print(f"Error getting balance: {e}")
            return False, 0.0
    
    def place_order(self, pair: str, side: str, order_type: str, volume: float) -> Tuple[bool, str]:
        """Place an order on Kraken"""
        try:
            if not self.api_key:
                return False, "API key not configured"
            
            kraken_pair = self._convert_pair_to_kraken(pair)
            
            order_data = {
                'pair': kraken_pair,
                'type': side,
                'ordertype': order_type,
                'volume': str(volume),
            }
            
            response = self.api.query_private('AddOrder', order_data)
            
            if response.get('error'):
                error_msg = response['error']
                return False, f"Order failed: {error_msg}"
            
            result = response.get('result', {})
            txid = result.get('txid', [])
            
            if txid:
                return True, f"Order placed successfully (TXID: {txid[0]})"
            else:
                return True, "Order placed successfully"
            
        except Exception as e:
            return False, f"Order placement error: {str(e)}"
    
    def get_open_orders(self) -> Dict[str, Any]:
        """Get all open orders"""
        try:
            response = self.api.query_private('OpenOrders')
            return response
        except Exception as e:
            print(f"Error getting open orders: {e}")
            return {}
    
    def cancel_order(self, txid: str) -> Tuple[bool, str]:
        """Cancel an order"""
        try:
            response = self.api.query_private('CancelOrder', {'txid': txid})
            
            if response.get('error'):
                return False, f"Cancel failed: {response['error']}"
            
            return True, "Order cancelled successfully"
            
        except Exception as e:
            return False, f"Cancel error: {str(e)}"
    
    def _convert_pair_to_kraken(self, pair: str) -> str:
        """Convert standard pair format to Kraken format"""
        pair_map = {
            'BTC/USD': 'XXBTZUSD',
            'ETH/USD': 'XETHZUSD',
            'SOL/USD': 'SOLUSD',
            'ADA/USD': 'ADAUSD',
            'DOT/USD': 'DOTUSD',
            'XRP/USD': 'XRPUSD',
        }
        return pair_map.get(pair, pair.replace('/', ''))
    
    def get_ticker_from_cache(self, pair: str) -> Optional[float]:
        """Get ticker price with caching"""
        # Simple implementation - in production, you'd want proper caching
        return self.get_ticker(pair)