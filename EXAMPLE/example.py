from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order


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

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        # Initialize the method output dict as an empty dict
        result = {}

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

                if best_bid and best_bid > acceptable_price * 1.05:
                    volume = min(order_depth.buy_orders[best_bid], self.position_limits[product] - current_position)

                if volume != 0:
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
        return result, 1, "SAMPLE"

        """
          # Note that this value of 1 is just a dummy value, you should likely change it!
            acceptable_price = 1

            # If statement checks if there are any SELL orders in the market
            if len(order_depth.sell_orders) > 0:

                # Sort all the available sell orders by their price,
                # and select only the sell order with the lowest price
                best_ask = min(order_depth.sell_orders.keys())
                best_ask_volume = order_depth.sell_orders[best_ask]

                # Check if the lowest ask (sell order) is lower than the above defined fair value
                if best_ask < acceptable_price:
                    # In case the lowest ask is lower than our fair value,
                    # This presents an opportunity for us to buy cheaply
                    # The code below therefore sends a BUY order at the price level of the ask,
                    # with the same quantity
                    # We expect this order to trade with the sell order
                    print("BUY", str(-best_ask_volume) + "x", best_ask)
                    orders.append(Order(product, best_ask, -best_ask_volume))

            # The below code block is similar to the one above,
            # the difference is that it find the highest bid (buy order)
            # If the price of the order is higher than the fair value
            # This is an opportunity to sell at a premium
            if len(order_depth.buy_orders) != 0:
                best_bid = max(order_depth.buy_orders.keys())
                best_bid_volume = order_depth.buy_orders[best_bid]
                if best_bid > acceptable_price:
                    print("SELL", str(best_bid_volume) + "x", best_bid)
                    orders.append(Order(product, best_bid, -best_bid_volume))

            # Add all the above the orders to the result dict
            result[product] = orders

        traderData = "SAMPLE"  # String value holding Trader state data required. It will be delivered as TradingState.traderData on next execution.

        conversions = 1

        # Return the dict of orders
        # These possibly contain buy or sell orders
        # Depending on the logic above

        return result, conversions, traderData

    """