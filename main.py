import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import asyncio
import json
import os
from pathlib import Path
import yaml

# Import custom modules
from kraken_api import KrakenAPI
from trading_logic import TradingStrategy

# Page configuration
st.set_page_config(
    page_title="Kraken RSI Trading Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .profit-positive {
        color: #10B981;
        font-weight: bold;
    }
    .profit-negative {
        color: #EF4444;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1E293B;
        border-radius: 5px 5px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

class TradingBot:
    def __init__(self):
        self.initialize_session_state()
        self.load_config()
        self.kraken_api = KrakenAPI(
            api_key=st.session_state.get('api_key', ''),
            api_secret=st.session_state.get('api_secret', ''),
            sandbox=st.session_state.get('sandbox_mode', True)
        )
        self.strategy = TradingStrategy()
    
    def _get_base_price_for_pair(self, pair):
        """Get typical base price for a trading pair"""
        base_prices = {
            'BTC/USD': 50000,
            'ETH/USD': 3000,
            'SOL/USD': 150,
            'ADA/USD': 0.50,
            'DOT/USD': 7,
            'XRP/USD': 0.60
        }
        return base_prices.get(pair, 100)
    
    def _generate_initial_prices(self, pair='BTC/USD'):
        """Generate initial simulated price data for charts"""
        base_price = self._get_base_price_for_pair(pair)
        prices = [base_price]
        for _ in range(99):
            volatility = 0.002
            change = prices[-1] * volatility * (np.random.random() - 0.5)
            prices.append(prices[-1] + change)
        return prices
        
    def initialize_session_state(self):
        """Initialize all session state variables"""
        defaults = {
            'trading_active': False,
            'trading_mode': 'simulation',  # 'simulation' or 'live'
            'balance': 10000.0,
            'real_balance': 0.0,
            'current_position': None,  # None, 'long', or 'short'
            'entry_price': 0.0,
            'position_size': 0.0,
            'trades': [],
            'prices': [],
            'rsi_values': [],
            'last_update': None,
            'api_key': '',
            'api_secret': '',
            'sandbox_mode': True,
            'performance': {
                'total_trades': 0,
                'winning_trades': 0,
                'total_profit': 0.0,
                'max_drawdown': 0.0,
                'peak_balance': 10000.0
            },
            'config': {
                'rsi_length': 14,
                'overbought': 70,
                'oversold': 30,
                'stop_loss': 2.0,
                'take_profit': 4.0,
                'position_size_pct': 10,
                'trading_pair': 'BTC/USD',
                'timeframe': '1m'
            },
            'last_trading_pair': 'BTC/USD'
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
        
        # Generate initial price data if empty or trading pair changed
        current_pair = st.session_state.config.get('trading_pair', 'BTC/USD')
        pair_changed = st.session_state.get('last_trading_pair') != current_pair
        
        if len(st.session_state.prices) == 0 or pair_changed:
            st.session_state.prices = self._generate_initial_prices(current_pair)
            st.session_state.rsi_values = []
            st.session_state.last_trading_pair = current_pair
            # Pre-calculate RSI values for initial prices
            for i in range(len(st.session_state.prices)):
                if i < 14:
                    st.session_state.rsi_values.append(50)
                else:
                    prices = st.session_state.prices[:i+1]
                    deltas = np.diff(prices[-15:])
                    gains = np.where(deltas > 0, deltas, 0)
                    losses = np.where(deltas < 0, -deltas, 0)
                    avg_gain = np.mean(gains)
                    avg_loss = np.mean(losses)
                    if avg_loss == 0:
                        rsi = 100
                    else:
                        rs = avg_gain / avg_loss
                        rsi = 100 - (100 / (1 + rs))
                    st.session_state.rsi_values.append(rsi)
                
    def load_config(self):
        """Load configuration from YAML file"""
        config_path = Path('config.yaml')
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                if 'api_key' in config:
                    st.session_state.api_key = config['api_key']
                if 'api_secret' in config:
                    st.session_state.api_secret = config['api_secret']
                if 'sandbox_mode' in config:
                    st.session_state.sandbox_mode = config['sandbox_mode']
    
    def save_config(self):
        """Save configuration to YAML file"""
        config = {
            'api_key': st.session_state.get('api_key', ''),
            'api_secret': st.session_state.get('api_secret', ''),
            'sandbox_mode': st.session_state.get('sandbox_mode', True)
        }
        
        with open('config.yaml', 'w') as f:
            yaml.dump(config, f)
    
    def render_header(self):
        """Render the page header"""
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown('<h1 class="main-header">📈 Kraken RSI Trading Bot</h1>', unsafe_allow_html=True)
            st.markdown("Real-time trading with Kraken API • Simulation & Live Modes")
        
        with col2:
            mode = st.session_state.trading_mode.upper()
            status_color = "#10B981" if st.session_state.trading_active else "#EF4444"
            status_text = "ACTIVE" if st.session_state.trading_active else "STOPPED"
            
            st.markdown(f"""
            <div style="background-color: #1E293B; padding: 10px; border-radius: 5px; text-align: center;">
                <div style="color: #94A3B8; font-size: 12px;">MODE</div>
                <div style="color: #F59E0B; font-size: 18px; font-weight: bold;">{mode}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="background-color: #1E293B; padding: 10px; border-radius: 5px; text-align: center;">
                <div style="color: #94A3B8; font-size: 12px;">STATUS</div>
                <div style="color: {status_color}; font-size: 18px; font-weight: bold;">{status_text}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
    
    def render_metrics(self):
        """Render key metrics dashboard"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            balance = st.session_state.real_balance if st.session_state.trading_mode == 'live' else st.session_state.balance
            balance_text = f"${balance:,.2f}"
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 14px; opacity: 0.9;">Account Balance</div>
                <div style="font-size: 28px; font-weight: bold;">{balance_text}</div>
                <div style="font-size: 12px; margin-top: 5px;">Mode: {st.session_state.trading_mode.upper()}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            position_type = st.session_state.current_position.upper() if st.session_state.current_position else "FLAT"
            position_color = "#10B981" if st.session_state.current_position == 'long' else "#EF4444" if st.session_state.current_position == 'short' else "#94A3B8"
            
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 14px; opacity: 0.9;">Current Position</div>
                <div style="font-size: 28px; font-weight: bold; color: {position_color}">{position_type}</div>
                <div style="font-size: 12px; margin-top: 5px;">Entry: ${st.session_state.entry_price:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            win_rate = (st.session_state.performance['winning_trades'] / st.session_state.performance['total_trades'] * 100) if st.session_state.performance['total_trades'] > 0 else 0
            win_rate_text = f"{win_rate:.1f}%"
            
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 14px; opacity: 0.9;">Win Rate</div>
                <div style="font-size: 28px; font-weight: bold;">{win_rate_text}</div>
                <div style="font-size: 12px; margin-top: 5px;">Trades: {st.session_state.performance['total_trades']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            total_pnl = st.session_state.balance - 10000
            pnl_color = "#10B981" if total_pnl >= 0 else "#EF4444"
            pnl_text = f"+${total_pnl:,.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):,.2f}"
            
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 14px; opacity: 0.9;">Total P&L</div>
                <div style="font-size: 28px; font-weight: bold; color: {pnl_color}">{pnl_text}</div>
                <div style="font-size: 12px; margin-top: 5px;">From $10,000</div>
            </div>
            """, unsafe_allow_html=True)
    
    def render_controls(self):
        """Render trading control buttons"""
        st.markdown("### Trading Controls")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("▶️ Start Trading", type="primary", use_container_width=True):
                self.start_trading()
        
        with col2:
            if st.button("⏹️ Stop Trading", type="secondary", use_container_width=True):
                self.stop_trading()
        
        with col3:
            if st.button("📈 Manual Buy", use_container_width=True):
                self.place_manual_trade('long')
        
        with col4:
            if st.button("📉 Manual Sell", use_container_width=True):
                self.place_manual_trade('short')
        
        with col5:
            if st.button("🏁 Close Position", use_container_width=True):
                self.close_position()
    
    def render_charts(self):
        """Render price and RSI charts"""
        tab1, tab2 = st.tabs(["📊 Price & RSI", "📈 Candlestick"])
        
        with tab1:
            if len(st.session_state.prices) > 10:
                self.create_line_chart()
            else:
                st.info("Waiting for more price data...")
        
        with tab2:
            self.create_candlestick_chart()
    
    def create_line_chart(self):
        """Create line chart with price and RSI"""
        fig = go.Figure()
        
        # Price line
        fig.add_trace(go.Scatter(
            x=list(range(len(st.session_state.prices))),
            y=st.session_state.prices,
            mode='lines',
            name='Price',
            line=dict(color='#3B82F6', width=2),
            yaxis='y'
        ))
        
        # RSI line
        if len(st.session_state.rsi_values) > 0:
            fig.add_trace(go.Scatter(
                x=list(range(len(st.session_state.rsi_values))),
                y=st.session_state.rsi_values,
                mode='lines',
                name='RSI',
                line=dict(color='#F59E0B', width=2),
                yaxis='y2'
            ))
        
        # Overbought/oversold lines
        fig.add_hline(
            y=st.session_state.config['overbought'],
            line_dash="dash",
            line_color="#EF4444",
            yref="y2",
            opacity=0.5
        )
        
        fig.add_hline(
            y=st.session_state.config['oversold'],
            line_dash="dash",
            line_color="#10B981",
            yref="y2",
            opacity=0.5
        )
        
        fig.update_layout(
            title="Price & RSI Chart",
            xaxis_title="Time",
            yaxis_title="Price ($)",
            yaxis2=dict(
                title="RSI",
                overlaying="y",
                side="right",
                range=[0, 100]
            ),
            template="plotly_dark",
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def create_candlestick_chart(self):
        """Create candlestick chart"""
        # For demo, generate synthetic candlestick data
        dates = pd.date_range(end=datetime.now(), periods=100, freq='1min')
        open_prices = np.random.normal(50000, 1000, 100).cumsum()
        high_prices = open_prices + np.random.uniform(50, 200, 100)
        low_prices = open_prices - np.random.uniform(50, 200, 100)
        close_prices = open_prices + np.random.normal(0, 100, 100)
        
        fig = go.Figure(data=[go.Candlestick(
            x=dates,
            open=open_prices,
            high=high_prices,
            low=low_prices,
            close=close_prices,
            increasing_line_color='#10B981',
            decreasing_line_color='#EF4444'
        )])
        
        fig.update_layout(
            title="Candlestick Chart (BTC/USD)",
            xaxis_title="Time",
            yaxis_title="Price ($)",
            template="plotly_dark",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_trade_history(self):
        """Render trade history table"""
        st.markdown("### Trade History")
        
        if not st.session_state.trades:
            st.info("No trades yet. Start trading to see history.")
            return
        
        # Convert trades to DataFrame
        trades_df = pd.DataFrame(st.session_state.trades)
        
        # Format columns
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        trades_df['profit'] = trades_df['profit'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
        trades_df['profit_pct'] = trades_df['profit_pct'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
        
        # Display table
        st.dataframe(
            trades_df,
            column_config={
                "timestamp": "Time",
                "type": "Type",
                "entry_price": "Entry Price",
                "exit_price": "Exit Price",
                "size": "Size",
                "profit": "Profit",
                "profit_pct": "Profit %",
                "mode": "Mode",
                "status": "Status"
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Export button
        if st.button("📥 Export as CSV"):
            csv = trades_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    def render_configuration(self):
        """Render configuration panel"""
        st.markdown("### Trading Configuration")
        
        with st.form("config_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.session_state.config['rsi_length'] = st.slider(
                    "RSI Length",
                    min_value=5,
                    max_value=30,
                    value=st.session_state.config['rsi_length'],
                    help="Period for RSI calculation"
                )
                
                st.session_state.config['overbought'] = st.slider(
                    "Overbought Level",
                    min_value=60,
                    max_value=90,
                    value=st.session_state.config['overbought'],
                    help="RSI level to trigger sell/short signals"
                )
                
                st.session_state.config['stop_loss'] = st.slider(
                    "Stop Loss %",
                    min_value=0.5,
                    max_value=10.0,
                    value=st.session_state.config['stop_loss'],
                    step=0.1,
                    help="Maximum loss percentage before closing position"
                )
            
            with col2:
                st.session_state.config['oversold'] = st.slider(
                    "Oversold Level",
                    min_value=10,
                    max_value=40,
                    value=st.session_state.config['oversold'],
                    help="RSI level to trigger buy/long signals"
                )
                
                st.session_state.config['take_profit'] = st.slider(
                    "Take Profit %",
                    min_value=1.0,
                    max_value=20.0,
                    value=st.session_state.config['take_profit'],
                    step=0.1,
                    help="Target profit percentage before closing position"
                )
                
                st.session_state.config['position_size_pct'] = st.slider(
                    "Position Size %",
                    min_value=1,
                    max_value=100,
                    value=st.session_state.config['position_size_pct'],
                    help="Percentage of account to use per trade"
                )
            
            col3, col4 = st.columns(2)
            
            with col3:
                st.session_state.config['trading_pair'] = st.selectbox(
                    "Trading Pair",
                    ["BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "DOT/USD", "XRP/USD"],
                    index=["BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "DOT/USD", "XRP/USD"].index(st.session_state.config['trading_pair'])
                )
            
            with col4:
                st.session_state.config['timeframe'] = st.selectbox(
                    "Timeframe",
                    ["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
                    index=["1m", "5m", "15m", "30m", "1h", "4h", "1d"].index(st.session_state.config.get('timeframe', '1m')),
                    help="Chart timeframe for analysis"
                )
            
            if st.form_submit_button("💾 Save Configuration"):
                st.success("Configuration saved!")
                st.rerun()
    
    def render_api_settings(self):
        """Render API settings panel"""
        st.markdown("### Kraken API Configuration")
        
        with st.form("api_form"):
            api_key = st.text_input(
                "API Key",
                value=st.session_state.get('api_key', ''),
                type="password",
                help="Your Kraken API Key"
            )
            
            api_secret = st.text_input(
                "API Secret",
                value=st.session_state.get('api_secret', ''),
                type="password",
                help="Your Kraken API Secret"
            )
            
            sandbox_mode = st.toggle(
                "Use Sandbox/Testnet",
                value=st.session_state.get('sandbox_mode', True),
                help="Use Kraken's test environment (recommended for testing)"
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                test_btn = st.form_submit_button("🔗 Test Connection", type="primary")
            
            with col2:
                save_btn = st.form_submit_button("💾 Save Keys")
            
            with col3:
                clear_btn = st.form_submit_button("🗑️ Clear Keys")
            
            if test_btn and api_key and api_secret:
                with st.spinner("Testing connection..."):
                    success, message = self.kraken_api.test_connection(api_key, api_secret, sandbox_mode)
                    if success:
                        st.success(message)
                        # Update real balance
                        if st.session_state.trading_mode == 'live':
                            self.update_real_balance()
                    else:
                        st.error(message)
            
            if save_btn:
                st.session_state.api_key = api_key
                st.session_state.api_secret = api_secret
                st.session_state.sandbox_mode = sandbox_mode
                self.save_config()
                st.success("API keys saved!")
            
            if clear_btn:
                st.session_state.api_key = ''
                st.session_state.api_secret = ''
                st.session_state.sandbox_mode = True
                self.save_config()
                st.warning("API keys cleared!")
    
    def render_mode_selector(self):
        """Render trading mode selector"""
        st.markdown("### Trading Mode")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "🎮 Simulation Mode",
                use_container_width=True,
                type="primary" if st.session_state.trading_mode == 'simulation' else "secondary"
            ):
                st.session_state.trading_mode = 'simulation'
                st.rerun()
        
        with col2:
            if st.button(
                "💎 Live Trading Mode",
                use_container_width=True,
                type="primary" if st.session_state.trading_mode == 'live' else "secondary",
                disabled=not (st.session_state.api_key and st.session_state.api_secret)
            ):
                st.session_state.trading_mode = 'live'
                # Test connection and update balance
                success, message = self.kraken_api.test_connection(
                    st.session_state.api_key,
                    st.session_state.api_secret,
                    st.session_state.sandbox_mode
                )
                if success:
                    st.success(f"Switched to Live Mode: {message}")
                    self.update_real_balance()
                else:
                    st.error(f"Failed to connect: {message}")
                    st.session_state.trading_mode = 'simulation'
                st.rerun()
    
    # Trading logic methods
    def start_trading(self):
        """Start the trading bot"""
        st.session_state.trading_active = True
        st.session_state.last_update = datetime.now()
        st.success("Trading started!")
        
        # Start background updates
        if 'update_thread' not in st.session_state:
            st.session_state.update_thread = True
            self.update_market_data()
    
    def stop_trading(self):
        """Stop the trading bot"""
        st.session_state.trading_active = False
        st.warning("Trading stopped!")
    
    def place_manual_trade(self, trade_type):
        """Place a manual trade"""
        if st.session_state.current_position:
            st.error("Already in a position. Close current position first.")
            return
        
        # Get current price (simulated or real)
        current_price = self.get_current_price()
        
        # Calculate position size
        account_balance = st.session_state.real_balance if st.session_state.trading_mode == 'live' else st.session_state.balance
        position_value = account_balance * (st.session_state.config['position_size_pct'] / 100)
        position_size = position_value / current_price
        
        # Record trade
        trade = {
            'timestamp': datetime.now(),
            'type': trade_type,
            'entry_price': current_price,
            'size': position_size,
            'mode': st.session_state.trading_mode,
            'status': 'OPEN'
        }
        
        st.session_state.trades.append(trade)
        st.session_state.current_position = trade_type
        st.session_state.entry_price = current_price
        st.session_state.position_size = position_size
        
        # Update balance for simulation mode
        if st.session_state.trading_mode == 'simulation' and trade_type == 'long':
            st.session_state.balance -= position_value
        
        st.success(f"{trade_type.upper()} position opened at ${current_price:,.2f}")
        
        # If live mode, execute on Kraken
        if st.session_state.trading_mode == 'live':
            self.execute_real_trade(trade_type, current_price, position_size)
    
    def close_position(self):
        """Close the current position"""
        if not st.session_state.current_position:
            st.error("No position to close")
            return
        
        current_price = self.get_current_price()
        trade_type = st.session_state.current_position
        profit = 0
        
        # Calculate profit
        if trade_type == 'long':
            profit = (current_price - st.session_state.entry_price) * st.session_state.position_size
            # Add back to balance for simulation
            if st.session_state.trading_mode == 'simulation':
                st.session_state.balance += st.session_state.position_size * current_price
        else:  # short
            profit = (st.session_state.entry_price - current_price) * st.session_state.position_size
        
        # Update performance
        st.session_state.performance['total_trades'] += 1
        st.session_state.performance['total_profit'] += profit
        if profit > 0:
            st.session_state.performance['winning_trades'] += 1
        
        # Update trade record
        for trade in reversed(st.session_state.trades):
            if trade['status'] == 'OPEN':
                trade['exit_price'] = current_price
                trade['exit_time'] = datetime.now()
                trade['profit'] = profit
                trade['profit_pct'] = (profit / (trade['entry_price'] * trade['size'])) * 100
                trade['status'] = 'CLOSED'
                break
        
        # Reset position
        st.session_state.current_position = None
        st.session_state.entry_price = 0
        st.session_state.position_size = 0
        
        profit_text = f"+${profit:,.2f}" if profit >= 0 else f"-${abs(profit):,.2f}"
        st.success(f"Position closed. Profit: {profit_text}")
        
        # If live mode, close on Kraken
        if st.session_state.trading_mode == 'live':
            self.execute_real_close(trade_type, current_price)
    
    def get_current_price(self):
        """Get current price (simulated or from Kraken)"""
        if st.session_state.trading_mode == 'live' and st.session_state.api_key:
            # Get real price from Kraken
            price = self.kraken_api.get_ticker(st.session_state.config['trading_pair'])
            if price:
                return price
        
        # Simulated price (random walk)
        if len(st.session_state.prices) > 0:
            last_price = st.session_state.prices[-1]
        else:
            last_price = self._get_base_price_for_pair(st.session_state.config['trading_pair'])
        
        # Random walk with volatility
        volatility = 0.002  # 0.2%
        change = last_price * volatility * (np.random.random() - 0.5)
        new_price = last_price + change
        
        # Update price history
        st.session_state.prices.append(new_price)
        if len(st.session_state.prices) > 200:
            st.session_state.prices.pop(0)
        
        # Update RSI
        self.update_rsi()
        
        return new_price
    
    def update_rsi(self):
        """Update RSI values"""
        if len(st.session_state.prices) < st.session_state.config['rsi_length'] + 1:
            st.session_state.rsi_values.append(50)
            return
        
        prices = st.session_state.prices[-st.session_state.config['rsi_length']-1:]
        deltas = np.diff(prices)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        st.session_state.rsi_values.append(rsi)
        if len(st.session_state.rsi_values) > 200:
            st.session_state.rsi_values.pop(0)
    
    def update_market_data(self):
        """Background task to update market data"""
        if st.session_state.trading_active:
            # Get new price
            current_price = self.get_current_price()
            
            # Check for trading signals
            if len(st.session_state.rsi_values) > 0:
                current_rsi = st.session_state.rsi_values[-1]
                
                # Buy signal (oversold)
                if current_rsi < st.session_state.config['oversold'] and not st.session_state.current_position:
                    self.place_manual_trade('long')
                
                # Sell signal (overbought)
                elif current_rsi > st.session_state.config['overbought'] and not st.session_state.current_position:
                    self.place_manual_trade('short')
                
                # Check stop loss/take profit
                if st.session_state.current_position:
                    self.check_position_limits(current_price)
            
            # Update last update time
            st.session_state.last_update = datetime.now()
    
    def check_position_limits(self, current_price):
        """Check if position hit stop loss or take profit"""
        if not st.session_state.current_position or st.session_state.entry_price == 0:
            return
        
        entry_price = st.session_state.entry_price
        profit_pct = 0
        
        if st.session_state.current_position == 'long':
            profit_pct = ((current_price - entry_price) / entry_price) * 100
        else:  # short
            profit_pct = ((entry_price - current_price) / entry_price) * 100
        
        # Check stop loss
        if profit_pct <= -st.session_state.config['stop_loss']:
            st.warning(f"Stop loss triggered: {profit_pct:.2f}%")
            self.close_position()
        
        # Check take profit
        elif profit_pct >= st.session_state.config['take_profit']:
            st.success(f"Take profit triggered: {profit_pct:.2f}%")
            self.close_position()
    
    def execute_real_trade(self, trade_type, price, size):
        """Execute a real trade on Kraken"""
        if not st.session_state.api_key:
            return
        
        success, message = self.kraken_api.place_order(
            pair=st.session_state.config['trading_pair'],
            side='buy' if trade_type == 'long' else 'sell',
            order_type='market',
            volume=size
        )
        
        if success:
            st.success(f"Real trade executed: {message}")
            self.update_real_balance()
        else:
            st.error(f"Trade failed: {message}")
    
    def execute_real_close(self, position_type, price):
        """Close a real position on Kraken"""
        if not st.session_state.api_key:
            return
        
        # Opposite side to close position
        side = 'sell' if position_type == 'long' else 'buy'
        
        success, message = self.kraken_api.place_order(
            pair=st.session_state.config['trading_pair'],
            side=side,
            order_type='market',
            volume=st.session_state.position_size
        )
        
        if success:
            st.success(f"Position closed: {message}")
            self.update_real_balance()
        else:
            st.error(f"Close failed: {message}")
    
    def update_real_balance(self):
        """Update real account balance from Kraken"""
        if not st.session_state.api_key:
            return
        
        success, balance = self.kraken_api.get_balance()
        if success:
            st.session_state.real_balance = balance
            st.rerun()
    
    def run(self):
        """Main run method"""
        self.render_header()
        
        # Sidebar
        with st.sidebar:
            st.markdown("## Navigation")
            page = st.radio(
                "Go to",
                ["📊 Dashboard", "⚙️ Configuration", "🔐 API Settings", "📋 Trade History", "📈 Charts"]
            )
            
            st.markdown("---")
            self.render_mode_selector()
            
            st.markdown("---")
            st.markdown("### Quick Stats")
            st.metric("Current Price", f"${self.get_current_price():,.2f}")
            if len(st.session_state.rsi_values) > 0:
                rsi = st.session_state.rsi_values[-1]
                rsi_color = "green" if rsi < 30 else "red" if rsi > 70 else "gray"
                st.metric("Current RSI", f"{rsi:.2f}", delta_color="off")
                st.markdown(f'<span style="color:{rsi_color}">{"Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"}</span>', unsafe_allow_html=True)
        
        # Main content based on selected page
        if page == "📊 Dashboard":
            self.render_metrics()
            self.render_controls()
            self.render_charts()
        
        elif page == "⚙️ Configuration":
            self.render_configuration()
        
        elif page == "🔐 API Settings":
            self.render_api_settings()
        
        elif page == "📋 Trade History":
            self.render_trade_history()
        
        elif page == "📈 Charts":
            self.render_charts()
        
        # Auto-refresh when trading is active
        if st.session_state.trading_active:
            self.update_market_data()
            time.sleep(1)
            st.rerun()

def main():
    bot = TradingBot()
    bot.run()

if __name__ == "__main__":
    main()