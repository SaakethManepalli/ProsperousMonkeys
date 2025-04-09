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
        # Position limits that will prevent over-trading
        self.position_limits = {

            "RAINFOREST_RESIN": 50, # Hard cap for stable commodity
            "KELP": 50,             # Hard cap for volatile commodity
            "SQUID_INK": 50         # Hard cap for patterned commodity

        }

        # Baseline price for each product
        self.acceptable_prices = {

            "RAINFOREST_RESIN": 10_000,  # Arbitrary average I chose for resin prices
            "KELP": 2_000,               # Arbitrary average I chose for kelp prices
            "SQUID_INK": 1_800           # Arbitrary average I chose for squid ink prices

        }

    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        # Initialize the method output dict as an empty dict
        result = {}
        conversions = 0
        trader_data = ""
        # Iterate over all the keys (the available products) contained in the order depth
        for product in state.order_depths.keys():

            # Retrieve the Order Depth containing all the market BUY and SELL orders
            order_depth: OrderDepth = state.order_depths[product]

            # Initialize the list of Orders to be sent as an empty list
            orders: list[Order] = []

            # Tracking current holdings
            current_position = state.position.get(product, 0)

            # Market analysis (finding the best prices)
            best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None

            # Spread for calcs based on volatility (emphasis on Kelp cuz we risky (◕‿↼) )
            spread = best_ask - best_bid if (best_ask and best_bid) else 0

            # Breaking down trading logic by product
            if product == "RAINFOREST_RESIN":
                acceptable_price = self.acceptable_prices[product]

                # Super Conservative strategy for stable assets
                if best_ask and best_ask < acceptable_price * 0.97:
                    volume = min(-order_depth.sell_orders[best_ask], self.position_limits[product] - current_position)

                    orders.append(Order(product, best_ask, volume))

                if best_bid and best_bid > acceptable_price * 1.03:
                    volume = min(order_depth.buy_orders[best_bid], self.position_limits[product] - current_position)

                    orders.append(Order(product, best_bid, volume))

            elif product == "KELP":
                acceptable_price = (best_ask + best_bid) / 2 if (best_ask and best_bid) else self.acceptable_prices[product]

                volume = 0  # Initialize volume

                # Sexy, aggressive, and mean like Ryan
                if best_ask and best_ask < acceptable_price * 0.95:
                    volume = min(-order_depth.sell_orders[best_ask], self.position_limits[product] - current_position)
                    if volume > 0:
                        orders.append(Order(product, best_ask, volume))

                if best_bid and best_bid > acceptable_price * 1.05:
                    volume = min(order_depth.buy_orders[best_bid], self.position_limits[product] - current_position)
                    if volume > 0:
                        orders.append(Order(product, best_bid, volume))


            elif product == "SQUID_INK":
                # Pattern detetcion
                acceptable_price = self.acceptable_prices[product]

                volume = 0

                if best_ask and best_ask < acceptable_price * 0.97:
                    volume = min(-order_depth.sell_orders[best_ask], self.position_limits[product] - current_position)

                    orders.append(Order(product, best_ask, volume))

                if best_bid and best_bid > acceptable_price * 1.03:
                    volume = min(order_depth.buy_orders[best_bid], self.position_limits[product] - current_position)

                if volume != 0:
                    orders.append(Order(product, best_bid, volume))

            result[product] = orders
            
        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data