#!/usr/bin/env python3
"""BTC 4-hour-ahead price forecast for make.fun bounty btc-cent-forecast-01.

Model: small-coefficient log-price mean reversion, validated against the
house persistence baseline (guess the checkpoint close) on three local
sets (Orca practice 6 cases, Orca Nov-10 64 cases, Coinbase BTC-USD
Oct 28-Nov 11 339 cases). It beats the baseline on all three:

    forecast = last * (geomean(last 6h) / last) ** 0.15
                    * (last / price_4h_ago) ** (-0.05)

Both terms are mean reversion: the first pulls the guess 15% of the way
back toward the 6-hour geometric mean, the second pulls it 5% against the
last 4-hour move. Coefficients are deliberately small: at a 4-hour horizon
BTC is close to a random walk, and an OLS fit of the same features flips
sign between halves of the validation data, so anything larger would be
fitting noise. No network, no randomness, stdlib only, deterministic.

Structure: :func:`forecast` is a thin composition over three helpers.
:func:`clean_prices` sanitises the raw series, :func:`mean_reversion_gap`
measures how far the last log-price sits from its 6-hour geometric mean,
and :func:`recent_move` measures the log-price move over the last 4 hours.
Splitting the helpers out keeps each step testable on its own without
changing any arithmetic: the forecast formula below is byte-for-byte the
same computation as the original single-function version.
"""
import json
import math
import os
from pathlib import Path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

# Model coefficients (see module docstring).
A_MEANREV = 0.15   # pull toward the 6h geometric mean
W_MEANREV = 360    # minutes of history for that mean
B_TREND = -0.05    # pull against the last 4h move
H_TREND = 240      # minutes for that move

MIN_PRICE = 0.00001
MAX_PRICE = 9_999_999.99999


def price5(x):
    """Keep a price on the scorer's 5-decimal grid inside (0, 10_000_000)."""
    return round(min(MAX_PRICE, max(MIN_PRICE, x)) * 1e5) / 1e5


def clean_prices(prices):
    """Return usable closes as floats, forward-filling bad entries.

    A bad entry (non-number, non-finite, or non-positive) is replaced by
    the most recent good price. Bad entries before the first good price
    are dropped, since there is nothing to fill them from.
    """
    clean = []
    last_good = None
    for p in prices:
        if isinstance(p, (int, float)) and math.isfinite(p) and p > 0:
            last_good = float(p)
            clean.append(last_good)
        elif last_good is not None:
            clean.append(last_good)
    if not clean:
        raise ValueError("no usable prices")
    return clean


def mean_reversion_gap(log_prices, window=W_MEANREV):
    """Log gap between the 6h geometric mean and the last log-price.

    The geometric mean of the last ``window`` prices is the arithmetic
    mean of their logs, so the gap is ``mean(logs[-window:]) - logs[-1]``.
    Positive when the recent mean sits above the last price: the forecast
    is then pulled upward. The window is capped at the series length.
    """
    w = min(window, len(log_prices))
    mean_w = sum(log_prices[-w:]) / w
    return mean_w - log_prices[-1]


def recent_move(log_prices, horizon=H_TREND):
    """Log-price move over the last ``horizon`` minutes.

    Returns ``logs[-1] - logs[-1 - horizon]``; zero when the series is too
    short to span the horizon (fewer than two usable prices). Positive
    after a rally: the forecast is then pulled downward, against the move.
    """
    h = min(horizon, len(log_prices) - 1)
    if h <= 0:
        return 0.0
    return log_prices[-1] - log_prices[-1 - h]


def forecast(prices):
    """One 4h-ahead price guess from 72h of 1-minute closes."""
    if not prices:
        raise ValueError("no prices")
    log_prices = [math.log(p) for p in clean_prices(prices)]
    last = log_prices[-1]
    gap = mean_reversion_gap(log_prices)
    move = recent_move(log_prices)
    return price5(math.exp(last + A_MEANREV * gap + B_TREND * move))


def main():
    in_dir = Path(INPUT_DIR)
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(in_dir.glob("*.in"))
    if not inputs:
        raise SystemExit(f"no .in files in {in_dir}")
    for path in inputs:
        case = json.loads(path.read_text(encoding="utf-8"))
        markets = case.get("markets")
        if not isinstance(markets, list) or len(markets) != 1:
            raise ValueError(f"{path.name} does not hold exactly one market")
        price = forecast(markets[0]["prices"])
        out = {"forecasts": [{"case": path.stem, "price": price}]}
        (out_dir / (path.stem + ".out")).write_text(
            json.dumps(out) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
