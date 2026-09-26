# fetchers.py — Mock price provider for development/testing
import random
import time

def get_mock_price(exchange: str, symbol: str) -> float:
    """
    Generate a random mock price for testing when live API calls are not desired.
    """
    s = symbol.upper()

    if s == "BTCUSDT":
        base = 60000
    elif s == "ETHUSDT":
        base = 3000
    elif s == "TRXUSDT":
        base = 0.12
    else:
        base = 100

    # Random price around base
    price = base + random.uniform(-0.5 * base * 0.01, 0.5 * base * 0.01)

    # Simulate network delay
    time.sleep(0.1)

    return round(price, 2)
