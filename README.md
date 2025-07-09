# pmm-natr-macd-inventory
# 🧠 Pure Market-Making Strategy: NATR + MACD + Inventory Control

This repository implements a lightweight, adaptive market-making bot that posts limit orders around the mid-price on a crypto market (e.g., ETH/USDT). The strategy leverages three key signals—**volatility, trend, and inventory levels**—to adjust spreads and order bias dynamically every 15 seconds.

---

## 📈 Strategy Overview

### Core Idea

We continuously maintain two-sided quoting (buy/sell limit orders) and adjust our strategy based on real-time market and position data. The three primary adjustment factors are:

1. Volatility (NATR)  
   - Uses the *Normalized Average True Range*.
   - Wider spreads in volatile markets reduce risk.
   - Tighter spreads in calm markets improve fill rates.

2. Trend (MACD)  
   - Uses the *Moving Average Convergence Divergence* indicator.
   - Skew orders in direction of trend (buy in uptrend, sell in downtrend).
   - Helps lean into short-term market momentum.

3. Inventory Control  
   - Monitors the current asset balance (ETH vs. USDT).
   - Dynamically adjusts quote placement to reduce imbalance.
   - Prevents overexposure to either asset.

---

## ⚙️ How It Works

### Quoting Logic

- Every 15 seconds, the bot:
  - Recalculates the mid-price.
  - Assesses volatility and trend from 30 × 1-minute bars.
  - Computes optimal spreads and skew.
  - Places new buy/sell limit orders with adjusted pricing.

### Signal Integration

| Signal     | Role                          | Response                          |
|------------|-------------------------------|------------------------------------|
| NATR       | Measures volatility            | Wider spreads in high volatility   |
| MACD       | Measures trend direction       | Skew quotes in trend direction     |
| Inventory  | Measures asset imbalance       | Favor underheld asset in quoting   |

---

## ⚖️ Assumptions & Trade-Offs

- Indicators use 30 one-minute candles for simplicity and speed.
- 15-second quote refresh offers balance between reactivity and system load.
- Fees, latency, and slippage are not included in this version—should be considered for production environments.
- Does not cross the spread; quotes remain outside top-of-book to avoid toxic fills and comply with conservative MM practices.

---

## 🛡 Risk Management

The strategy integrates multiple layers of risk controls:

- Adaptive Spreads: Protects against losses during high volatility.
- Trend Skewing: Reduces exposure to adverse price moves during trends.
- Inventory Penalties: Encourages neutrality in asset holdings.
- Quote Sanity Checks: Avoids crossing best bid/ask and ensures minimum spread of >1 basis point.

---

## 💡 Why This Works

- Multi-signal logic reduces exposure to isolated market risks.
- Extremely lightweight, can be run on a small server or VPS.
- Combines time-tested market-making principles in a modern, modular implementation.
- Suited for high-frequency, short-term crypto markets (e.g., 1-minute bars, 15s quote intervals).

---

## ✅ Bottom Line

> A simple yet powerful pure market-making strategy built for fast-moving crypto markets.  
> Focused on balanced, adaptive, and risk-aware quoting behavior.

---

## 📂 Repository Structure

```bash
.
├── strategy/
│   ├── market_maker.py        # Core logic for quoting & signal integration
│   ├── indicators.py          # NATR & MACD computation
│   └── inventory.py           # Inventory adjustment logic
├── config/
│   └── params.yml             # Parameter tuning and runtime configs
├── README.md
└── requirements.txt


