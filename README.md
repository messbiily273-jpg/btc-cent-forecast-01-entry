# btc-cent-forecast-01

BTC 4-hour-ahead price forecast for the make.fun bounty
[btc-cent-forecast-01](https://make.fun/bounty/btc-cent-forecast-01).

## Model

Small-coefficient log-price mean reversion, stdlib only, deterministic, no
network, no randomness:

```
forecast = last * (geomean(last 6h) / last) ** 0.15
                * (last / price_4h_ago) ** (-0.05)
```

The first term pulls the guess 15% of the way back toward the 6-hour
geometric mean; the second pulls it 5% against the last 4-hour move.
Coefficients are deliberately small: at a 4-hour horizon BTC is close to a
random walk, and an OLS fit of the same features flips sign between halves
of the validation data, so anything larger would be fitting noise.

## Usage

```
MAKEFUN_INPUT_DIR=<input dir> MAKEFUN_OUTPUT_DIR=<output dir> python3 main.py
```

Each `*.in` file holds one market with 72h of 1-minute closes; each run
writes `<id>.out` as `{"forecasts": [{"case": id, "price": <5-decimal number>}]}`.

## Local validation (mean absolute error, cents, lower is better)

| Set | Cases | Persistence baseline | This model |
| --- | --- | --- | --- |
| Orca practice (kit p00-p05) | 6 | 44,521.6 | **44,113.7** (-0.92%) |
| Orca Nov 10, 15-min checkpoints | 64 | 51,573.1 | **49,900.7** (-3.2%) |
| Coinbase BTC-USD Oct 28-Nov 11, hourly | 339 | 45,178.0 | **44,853.6** (-0.7%) |

Deterministic: two runs byte-identical.

## License

MIT. See LICENSE.
