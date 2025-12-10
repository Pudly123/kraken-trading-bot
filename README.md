# Kraken RSI Trading Bot

A professional trading bot built with Streamlit that can connect to Kraken for live trading or run in a local simulation mode.

## Features

- Real Kraken API integration (via `krakenex`)
- Simulation and Live modes
- RSI-based trading strategy with stop-loss/take-profit
- Simple Streamlit dashboard showing price, RSI, trade history and metrics

## Setup

1. Clone the repository

```bash
git clone https://github.com/yourusername/kraken-trading-bot.git
cd kraken-trading-bot
```

2. (Optional) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

## Running the Full Web UI Locally

This project uses Streamlit for the UI. Running locally does not require Streamlit Cloud credits.

Start the app on port 8050 (default in the included Streamlit config):

```bash
# make the helper script executable (first time only)
chmod +x run_local.sh

# run the app (uses port 8050 by default)
./run_local.sh 8050

# OR run directly
streamlit run main.py --server.port 8050 --server.headless true
```

Open your browser to http://localhost:8050 to view the full dashboard.

## Headless Test

If you only want to run a quick simulation (no UI), use the included headless test:

```bash
python run_headless_test.py
```

## Configuration

- API keys are read/written from `config.yaml` if present; do not commit that file containing secrets.
- Streamlit server defaults are in `.streamlit/config.toml` (port 8050, headless true).

## Next Steps / Troubleshooting

- If you see Streamlit UI issues, ensure your environment has the correct `requirements.txt` packages installed.
- If you want to host the UI remotely without Streamlit Cloud, you can deploy to a VM, Docker container, or another hosting provider and run the same `streamlit run` command.

If you want, I can try to start the server here and verify it — or guide you step-by-step while you run the `./run_local.sh` command and paste any output errors.
# Kraken RSI Trading Bot

A professional trading bot built with Streamlit that connects to Kraken exchange for real-time trading.

## Features

- **Real Kraken API Integration**: Connect to Kraken for live trading
- **Dual Mode**: Simulation mode for testing, Live mode for real trading
- **RSI Strategy**: Configurable RSI-based trading strategy
- **Risk Management**: Stop loss, take profit, position sizing
- **Real-time Dashboard**: Live charts and metrics
- **Trade History**: Track and export all trades

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/kraken-trading-bot.git
cd kraken-trading-bot