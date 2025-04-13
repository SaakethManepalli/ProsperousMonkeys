from typing import Dict, List
import json
from typing import Any
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[: max_length - 3] + "..."


logger = Logger()


class Trader:
    def __init__(self):
        self.position_limits = {
            "RAINFOREST_RESIN": 50,
            "KELP": 50,
            "SQUID_INK": 50,
            "CROISSANTS": 250,
            "DJEMBES": 60
        }

        self.acceptable_prices = {
            "RAINFOREST_RESIN": 10_000,
            "KELP": 2_000,
            "SQUID_INK": 1_870,
            "CROISSANTS": 4_270,
            "DJEMBES": 13_380
        }

        # Simple internal commodity tracking system
        self.commodity_history = {
            "RAINFOREST_RESIN": [],
            "KELP": [],
            "SQUID_INK": [],
            "CROISSANTS": [],
            "DJEMBES": []
        }

    def track_commodity(self, product: str, action: str, price: float, volume: int):
        event = {
            "timestamp": self.get_current_timestamp(),
            "action": action,
            "price": price,
            "volume": volume
        }
        self.commodity_history[product].append(event)

    def get_current_timestamp(self):
        # Replace with actual timestamp generator if needed
        import datetime
        return datetime.datetime.utcnow().isoformat()

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        result = {}
        conversions = 0
        trader_data = ""

        for product in state.order_depths.keys():
            order_depth: OrderDepth = state.order_depths[product]
            orders: list[Order] = []
            current_position = state.position.get(product, 0)

            best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None

            if product == "RAINFOREST_RESIN":
                acceptable_price = self.acceptable_prices[product]

                if best_ask and best_ask < acceptable_price * 0.9999:
                    volume = min(-order_depth.sell_orders[best_ask],
                                 self.position_limits[product] - current_position)
                    orders.append(Order(product, best_ask, volume))
                    self.track_commodity(product, "BUY", best_ask, volume)

                if best_bid and best_bid > acceptable_price * 1.0001:
                    volume = min(order_depth.buy_orders[best_bid],
                                 self.position_limits[product] - current_position)
                    orders.append(Order(product, best_bid, -volume))
                    self.track_commodity(product, "SELL", best_bid, volume)


            elif product == "KELP":
                acceptable_price = (best_ask + best_bid)/2 if (best_ask and best_bid) else self.acceptable_prices[product]

                if best_ask and best_ask < acceptable_price * 0.95:
                    volume = min(-order_depth.sell_orders[best_ask],
                                 self.position_limits[product] - current_position)
                    if volume > 0:
                        orders.append(Order(product, best_ask, volume))
                        self.track_commodity(product, "BUY", best_ask, volume)

                if best_bid and best_bid > acceptable_price * 1.05:
                    volume = min(order_depth.buy_orders[best_bid],
                                 self.position_limits[product] - current_position)
                    if volume > 0:
                        orders.append(Order(product, best_bid, -volume))
                        self.track_commodity(product, "SELL", best_bid, volume)

            elif product == "SQUID_INK":
                acceptable_price = self.acceptable_prices[product]

                if best_ask and best_ask < acceptable_price * 0.99:
                    volume = min(-order_depth.sell_orders[best_ask],
                                 self.position_limits[product] - current_position)
                    orders.append(Order(product, best_ask, volume))
                    self.track_commodity(product, "BUY", best_ask, volume)

                if best_bid and best_bid > acceptable_price * 1.01:
                    volume = min(order_depth.buy_orders[best_bid],
                                 self.position_limits[product] - current_position)
                    orders.append(Order(product, best_bid, -volume))
                    self.track_commodity(product, "SELL", best_bid, volume)

            elif product == "CROISSANTS":
                acceptable_price = self.acceptable_prices[product]

                if best_ask and best_ask < acceptable_price * 0.9999:
                    volume = min(-order_depth.sell_orders[best_ask],
                                 self.position_limits[product] - current_position)
                    orders.append(Order(product, best_ask, volume))
                    self.track_commodity(product, "BUY", best_ask, volume)

                if best_bid and best_bid > acceptable_price * 1.0001:
                    volume = min(order_depth.buy_orders[best_bid],
                                 self.position_limits[product] - current_position)
                    orders.append(Order(product, best_bid, -volume))
                    self.track_commodity(product, "SELL", best_bid, volume)

            elif product == "DJEMBES":
                acceptable_price = self.acceptable_prices[product]

                if best_ask and best_ask < acceptable_price * 0.99985 and best_ask > 13378 and best_ask < 13390:
                    volume = min(-order_depth.sell_orders[best_ask],
                                 self.position_limits[product] - current_position)
                    orders.append(Order(product, best_ask, volume))
                    self.track_commodity(product, "BUY", best_ask, volume)

                if best_bid and best_bid > acceptable_price * 1.00015 and best_bid < 13390 and best_bid > 13375:
                    volume = min(order_depth.buy_orders[best_bid],
                                 self.position_limits[product] - current_position)
                    orders.append(Order(product, best_bid, -volume))
                    self.track_commodity(product, "SELL", best_bid, volume)

            if orders:
                result[product] = orders

        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data
#Hello World
