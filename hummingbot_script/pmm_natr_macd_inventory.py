# -*- coding: utf-8 -*-
# File: pmm_natr_macd_inventory.py
# Pure market-making with dynamic spreads based on NATR, MACD histogram trend bias,
# and inventory-risk penalty

import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, List

import pandas as pd
import pandas_ta as ta  # bundled with Hummingbot

from hummingbot.core.data_type.common import OrderType, PriceType, TradeType
from hummingbot.core.data_type.order_candidate import OrderCandidate
from hummingbot.core.event.events import OrderFilledEvent
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase
from hummingbot.data_feed.candles_feed.candles_factory import CandlesFactory, CandlesConfig
from hummingbot.connector.connector_base import ConnectorBase


class PMMNatrMacdInventoryStrategy(ScriptStrategyBase):
    """
    Pure market-making strategy combining:
      • Volatility-adjusted spreads via NATR
      • Trend bias via MACD histogram
      • Inventory-risk penalty φ
    """

    trading_pair: str = "ETH-USDT"
    exchange: str = "binance_paper_trade"

    order_amount: Decimal = Decimal("0.01")
    order_refresh_time: int = 15  # seconds

    # Candles feed configuration
    candle_connector: str = "binance"
    candles_interval: str = "1m"
    natr_length: int = 30         # periods for NATR
    max_records: int = 1000

    # NATR spread scalers (fraction of price)
    bid_natr_scalar: Decimal = Decimal("120") / Decimal("10000")
    ask_natr_scalar: Decimal = Decimal("60") / Decimal("10000")

    # MACD parameters and weight
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    macd_weight: Decimal = Decimal("0.5")  # half-spread shift per unit MACD histogram

    # Inventory risk penalty
    inventory_phi: Decimal = Decimal("0.01")  # penalty per unit normalized inventory
    max_inventory: Decimal = Decimal("1")      # inventory cap for normalization

    markets = {exchange: {trading_pair}}

    candles = CandlesFactory.get_candle(
        CandlesConfig(
            connector=candle_connector,
            trading_pair=trading_pair,
            interval=candles_interval,
            max_records=max_records,
        )
    )

    def __init__(self, connectors: Dict[str, ConnectorBase]):
        super().__init__(connectors)
        self.candles.start()
        # last metrics for status
        self._last_bid_spread: Decimal = Decimal("0")
        self._last_ask_spread: Decimal = Decimal("0")
        self._last_inv_norm: Decimal = Decimal("0")

    def on_stop(self):
        self.candles.stop()

    def on_tick(self):
        # rate limit
        if self.current_timestamp < getattr(self, "_next_tick", 0):
            return
        if not self.ready_to_trade:
            return

        # fetch and augment candles
        df = self.candles.candles_df.copy()
        df.ta.natr(length=self.natr_length, append=True)
        df.ta.macd(fast=self.macd_fast,
                   slow=self.macd_slow,
                   signal=self.macd_signal,
                   append=True)

        # required columns
        natr_col = f"NATR_{self.natr_length}"
        macd_hist_col = f"MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"

        # readiness checks
        if (df.shape[0] < max(self.natr_length, self.macd_slow + self.macd_signal)
                or natr_col not in df or macd_hist_col not in df):
            return
        if pd.isna(df[natr_col].iloc[-1]) or pd.isna(df[macd_hist_col].iloc[-1]):
            return

        # compute NATR and MACD histogram
        try:
            natr = Decimal(str(df[natr_col].iloc[-1]))
        except (InvalidOperation, ValueError):
            return
        macd_hist = Decimal(str(df[macd_hist_col].iloc[-1]))

        # base spreads
        base_bid_spread = natr * self.bid_natr_scalar
        base_ask_spread = natr * self.ask_natr_scalar

        # trend skew adjustments
        bid_spread = base_bid_spread - self.macd_weight * macd_hist
        ask_spread = base_ask_spread + self.macd_weight * macd_hist

        # inventory penalty
        base_asset = self.trading_pair.split("-")[0]
        inv_pos = Decimal(self.connectors[self.exchange].get_balance(base_asset))
        inv_norm = max(min(inv_pos / self.max_inventory, Decimal(1)), Decimal(-1))
        bid_spread += self.inventory_phi * inv_norm
        ask_spread -= self.inventory_phi * inv_norm

        # store for status
        self._last_bid_spread = bid_spread
        self._last_ask_spread = ask_spread
        self._last_inv_norm = inv_norm

        # ensure minimum spreads
        min_spread = Decimal("0.00001")
        bid_spread = max(bid_spread, min_spread)
        ask_spread = max(ask_spread, min_spread)

        # reference mid price
        ref_price = Decimal(str(
            self.connectors[self.exchange]
                .get_price_by_type(self.trading_pair, PriceType.MidPrice)))

        buy_price = ref_price * (Decimal(1) - bid_spread)
        sell_price = ref_price * (Decimal(1) + ask_spread)

        # avoid crossing
        best_bid = Decimal(self.connectors[self.exchange].get_price(self.trading_pair, False))
        best_ask = Decimal(self.connectors[self.exchange].get_price(self.trading_pair, True))
        buy_price = min(buy_price, best_bid)
        sell_price = max(sell_price, best_ask)

        # cancel and place orders (allow partial funding)
        self.cancel_all_orders()
        orders: List[OrderCandidate] = [
            OrderCandidate(self.trading_pair, True, OrderType.LIMIT,
                           TradeType.BUY, self.order_amount, buy_price),
            OrderCandidate(self.trading_pair, True, OrderType.LIMIT,
                           TradeType.SELL, self.order_amount, sell_price),
        ]
        # use all_or_none=False to allow each leg independently
        adjusted = self.connectors[self.exchange] \
            .budget_checker.adjust_candidates(orders, all_or_none=False)  # partial funding
        for o in adjusted:
            if o.order_side == TradeType.BUY:
                self.buy(self.exchange, o.trading_pair, o.amount, o.order_type, o.price)
            elif o.order_side == TradeType.SELL:
                self.sell(self.exchange, o.trading_pair, o.amount, o.order_type, o.price)

        self._next_tick = self.current_timestamp + self.order_refresh_time

    def cancel_all_orders(self):
        for o in self.get_active_orders(self.exchange):
            self.cancel(self.exchange, o.trading_pair, o.client_order_id)

    def did_fill_order(self, event: OrderFilledEvent):
        msg = (f"{event.trade_type.name} {event.amount:.4f} "
               f"{event.trading_pair} @ {event.price:.2f}")
        self.log_with_clock(logging.INFO, msg)
        self.notify_hb_app_with_timestamp(msg)

    def format_status(self) -> str:
        if not self.ready_to_trade:
            return "Market connectors are not ready."
        return (
            f"Bid spread: {self._last_bid_spread*1e4:.2f} bps | "
            f"Ask spread: {self._last_ask_spread*1e4:.2f} bps | "
            f"Inv norm: {self._last_inv_norm:.3f}"
        )
