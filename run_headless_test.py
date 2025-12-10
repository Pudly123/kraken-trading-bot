import numpy as np
from trading_logic import TradingStrategy
from kraken_api import KrakenAPI

def generate_price_series(base=50000, n=500, volatility=0.002):
    prices = [base]
    for _ in range(n-1):
        change = prices[-1] * volatility * (np.random.random() - 0.5)
        prices.append(prices[-1] + change)
    return prices

def main():
    print("Starting headless test...")

    # Verify KrakenAPI import/instantiation
    try:
        api = KrakenAPI()
        print("KrakenAPI instantiated.")
    except Exception as e:
        print(f"KrakenAPI import/instantiation failed: {e}")

    # Run strategy simulation
    strategy = TradingStrategy()
    prices = generate_price_series()
    # Example config for both long and short
    config = dict(
        long_rsi_length=14,
        short_rsi_length=14,
        long_oversold=30,
        short_overbought=70,
        long_stop_loss=2.0,
        short_stop_loss=2.0,
        long_take_profit=4.0,
        short_take_profit=4.0,
        long_min_take_profit_enabled=True,
        short_min_take_profit_enabled=True,
        long_min_take_profit=1.0,
        short_min_take_profit=1.0,
        long_position_size_pct=10,
        short_position_size_pct=10
    )

    result = strategy.simulate_strategy(
        historical_prices=prices,
        initial_balance=10000,
        **config
    )

    print("Simulation results (with separate long/short settings):")
    print(f" Final balance: ${result['final_balance']:,.2f}")
    print(f" Total trades: {result['total_trades']}")
    print(f" Winning trades: {result['winning_trades']}")
    print(f" Win rate: {result['win_rate']:.2f}%")
    print(f" Total profit: ${result['total_profit']:,.2f}")

    if result['trades']:
        print(" First 5 trades:")
        for t in result['trades'][:5]:
            print(t)

if __name__ == '__main__':
    main()
