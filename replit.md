# Kraken RSI Trading Bot

## Overview
A professional trading bot built with Streamlit that connects to Kraken exchange for real-time trading using RSI (Relative Strength Index) strategy.

## Features
- Real Kraken API Integration for live trading
- Dual Mode: Simulation mode for testing, Live mode for real trading
- RSI-based trading strategy with configurable parameters
- Risk Management: Stop loss, take profit, position sizing
- Real-time Dashboard with live charts and metrics
- Trade History tracking with CSV export

## Project Structure
```
├── main.py           # Main Streamlit application with TradingBot class
├── kraken_api.py     # Kraken API wrapper for exchange connectivity
├── trading_logic.py  # RSI trading strategy implementation
├── requirements.txt  # Python dependencies
├── packages.txt      # System dependencies
└── config.yaml       # API configuration (gitignored)
```

## Running the Application
The app runs as a Streamlit web application on port 5000:
```bash
streamlit run main.py --server.address=0.0.0.0 --server.port=5000 --server.headless=true
```

## Configuration
- API keys can be configured through the web interface under "API Settings"
- Trading parameters (RSI length, overbought/oversold levels, stop loss, take profit) are configurable in the "Configuration" tab
- Supports simulation mode for testing without real funds

## Dependencies
- streamlit - Web application framework
- plotly - Interactive charts
- pandas/numpy - Data processing
- krakenex - Kraken API client
- ccxt - Cryptocurrency exchange library
- ta - Technical analysis library
- pyyaml - Configuration file handling

## Recent Changes
- December 10, 2025: Fixed simulation and configuration issues
  - Added auto-refresh when trading is active (1 second intervals)
  - Added trading pair change detection to regenerate prices with correct base price
  - Added timeframe configuration option (1m, 5m, 15m, 30m, 1h, 4h, 1d)
  - Each trading pair now starts with realistic simulated prices

- December 10, 2025: Initial setup for Replit environment
  - Fixed krakenex API initialization (removed unsupported 'tier' parameter)
  - Added session state initialization for api_key, api_secret, sandbox_mode
  - Configured Streamlit to run on 0.0.0.0:5000
