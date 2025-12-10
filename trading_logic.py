import numpy as np
import pandas as pd
from typing import List, Tuple, Optional

class TradingStrategy:
    def __init__(self):
        self.prices = []
        self.rsi_values = []
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI for given prices"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices[-period-1:])
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def get_signal(self, prices: List[float], rsi_period: int = 14, 
                   oversold: int = 30, overbought: int = 70) -> str:
        """Get trading signal based on RSI"""
        if len(prices) < rsi_period + 1:
            return "hold"
        
        rsi = self.calculate_rsi(prices, rsi_period)
        
        if rsi < oversold:
            return "buy"
        elif rsi > overbought:
            return "sell"
        else:
            return "hold"
    
    def calculate_position_size(self, account_balance: float, risk_per_trade: float,
                               stop_loss_pct: float, current_price: float) -> float:
        """Calculate position size based on risk management"""
        risk_amount = account_balance * (risk_per_trade / 100)
        stop_loss_amount = current_price * (stop_loss_pct / 100)
        
        if stop_loss_amount == 0:
            return 0
        
        position_size = risk_amount / stop_loss_amount
        return position_size
    
    def check_stop_loss(self, entry_price: float, current_price: float, 
                       stop_loss_pct: float, position_type: str) -> bool:
        """Check if stop loss has been hit"""
        if position_type == 'long':
            loss_pct = ((current_price - entry_price) / entry_price) * 100
            return loss_pct <= -stop_loss_pct
        elif position_type == 'short':
            loss_pct = ((entry_price - current_price) / entry_price) * 100
            return loss_pct <= -stop_loss_pct
        return False
    
    def check_take_profit(self, entry_price: float, current_price: float,
                         take_profit_pct: float, position_type: str) -> bool:
        """Check if take profit has been hit"""
        if position_type == 'long':
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            return profit_pct >= take_profit_pct
        elif position_type == 'short':
            profit_pct = ((entry_price - current_price) / entry_price) * 100
            return profit_pct >= take_profit_pct
        return False
    
    def simulate_strategy(self, historical_prices: List[float], initial_balance: float = 10000,
                         rsi_period: int = 14, oversold: int = 30, overbought: int = 70,
                         stop_loss: float = 2.0, take_profit: float = 4.0,
                         position_size_pct: float = 10) -> dict:
        """Simulate trading strategy on historical data"""
        balance = initial_balance
        position = None
        entry_price = 0
        position_size = 0
        trades = []
        
        for i in range(rsi_period + 1, len(historical_prices)):
            current_price = historical_prices[i]
            price_window = historical_prices[:i+1]
            
            # Get RSI signal
            rsi = self.calculate_rsi(price_window, rsi_period)
            
            if position is None:
                # Check for entry signal
                if rsi < oversold:
                    # Buy signal
                    position = 'long'
                    entry_price = current_price
                    position_value = balance * (position_size_pct / 100)
                    position_size = position_value / entry_price
                    balance -= position_value
                    
                    trades.append({
                        'type': 'long',
                        'entry_price': entry_price,
                        'entry_time': i,
                        'size': position_size
                    })
                    
                elif rsi > overbought:
                    # Sell signal (short)
                    position = 'short'
                    entry_price = current_price
                    position_value = balance * (position_size_pct / 100)
                    position_size = position_value / entry_price
                    
                    trades.append({
                        'type': 'short',
                        'entry_price': entry_price,
                        'entry_time': i,
                        'size': position_size
                    })
            
            else:
                # Check for exit signals
                if position == 'long':
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                    
                    if profit_pct <= -stop_loss or profit_pct >= take_profit or rsi > overbought:
                        # Exit long position
                        balance += position_size * current_price
                        
                        trades[-1]['exit_price'] = current_price
                        trades[-1]['exit_time'] = i
                        trades[-1]['profit'] = (current_price - entry_price) * position_size
                        trades[-1]['profit_pct'] = profit_pct
                        
                        position = None
                        entry_price = 0
                        position_size = 0
                
                elif position == 'short':
                    profit_pct = ((entry_price - current_price) / entry_price) * 100
                    
                    if profit_pct <= -stop_loss or profit_pct >= take_profit or rsi < oversold:
                        # Exit short position
                        trades[-1]['exit_price'] = current_price
                        trades[-1]['exit_time'] = i
                        trades[-1]['profit'] = (entry_price - current_price) * position_size
                        trades[-1]['profit_pct'] = profit_pct
                        
                        position = None
                        entry_price = 0
                        position_size = 0
        
        # Close any open position at the end
        if position is not None:
            if position == 'long':
                balance += position_size * historical_prices[-1]
                trades[-1]['exit_price'] = historical_prices[-1]
                trades[-1]['exit_time'] = len(historical_prices) - 1
                trades[-1]['profit'] = (historical_prices[-1] - entry_price) * position_size
                trades[-1]['profit_pct'] = ((historical_prices[-1] - entry_price) / entry_price) * 100
        
        # Calculate performance metrics
        total_trades = len([t for t in trades if 'profit' in t])
        winning_trades = len([t for t in trades if 'profit' in t and t['profit'] > 0])
        total_profit = sum([t.get('profit', 0) for t in trades])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'final_balance': balance,
            'total_return': ((balance - initial_balance) / initial_balance) * 100,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'trades': trades
        }