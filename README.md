# pmm-natr-macd-inventory
Pure market-making bot for ETH–USDT combining NATR, MACD trend skew, and inventory control.

Overview:

In this project, I design and implement a pure market-making algorithm for the ETH–USDT pair using Hummingbot. Rather than static spreads, my bot continuously adapts its quoting behavior by blending three real-time signals:

Volatility Sizing (NATR):

Computes the 30-period Normalized Average True Range on one-minute candles.

Dynamically scales base bid/ask half-spreads—wider when markets are choppy, tighter when calm—so we’re always compensated for risk.

Trend Bias (MACD Histogram):

Uses the classic MACD(12,26,9) histogram to measure short-term momentum.

Leans into price moves by narrowing the spread on the side of the trend (buy more aggressively in an up-trend, sell more aggressively in a down-trend), capturing directional drift.

Inventory Penalty (φ):

Normalizes our net ETH position to [–1,1] and applies a linear penalty (φ) to skew quotes against large balances.

Prevents the bot from accumulating runaway one-sided exposure and keeps inventory near zero.

Methodology & Structure
Data Feed: 1-minute OHLCV candles from Binance.

Cadence: Recomputes every 15 seconds—canceling stale orders and placing new bids/asks around the mid-price (1±spread), always outside the current best bid/ask and no tighter than 1 basis point.

Risk Controls:

Adaptive spreads to limit adverse selection,

Trend skew to avoid selling into strength or buying into weakness,

Inventory mean-reversion to manage P&L volatility.
